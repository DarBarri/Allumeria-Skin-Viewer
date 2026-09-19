#!/usr/bin/env python3
"""Minimal standalone Allumeria 3D skin viewer.
Dependencies: Pillow only. Tkinter is part of standard Python on normal desktop
Python installations. Optional: tkinterdnd2 (for drag-and-drop support).
Usage:
python allumeria_viewer.py skin.png
python allumeria_viewer.py skin.png --watch
Controls:
Left mouse drag       Orbit (drag model naturally)
Mouse wheel           Zoom
R / Space             Refresh texture from disk
F                     Reset camera
1 / 2 / 3 / 4 / 5 / 6 Front/Right/Back/Left/Top/Bottom
Esc                   Quit
"""
import argparse
import math
import os
import sys
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageDraw, ImageTk

# Optional dependency for Drag-and-Drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

# -----------------------------------------------------------------------------
# Small vector/matrix helpers
# -----------------------------------------------------------------------------
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])
def length(a): return math.sqrt(dot(a, a))
def norm(a):
    n = length(a)
    return (a[0]/n, a[1]/n, a[2]/n) if n else (0.0, 0.0, 0.0)

def rot_xyz(p, rx, ry, rz):
    sx, cx = math.sin(rx), math.cos(rx)
    sy, cy = math.sin(ry), math.cos(ry)
    sz, cz = math.sin(rz), math.cos(rz)
    x, y, z = p
    return (
        x*(cx*cy) + y*(cx*sy*sz - sx*cz) + z*(cx*sy*cz + sx*sz),
        x*(sx*cy) + y*(sx*sy*sz + cx*cz) + z*(sx*sy*cz - cx*sz),
        x*(-sy)  + y*(cy*sz)             + z*(cy*cz),
    )

def camera_orbit(p, yaw, pitch):
    # Orbit transform used only by the camera.
    x, y, z = p
    sy, cy = math.sin(yaw), math.cos(yaw)
    # Y-axis yaw
    x, z = x * cy + z * sy, -x * sy + z * cy
    sp, cp = -math.sin(pitch), math.cos(pitch)
    # X-axis pitch
    y, z = y * cp - z * sp, y * sp + z * cp
    return (x, y, z)

# -----------------------------------------------------------------------------
# Geometry. Coordinates and UVs are copied from the Allumeria model.
# -----------------------------------------------------------------------------
CUBE_FACES = [
    (0, 1, 2, 3),  # FRONT
    (1, 5, 3, 7),  # LEFT
    (5, 4, 7, 6),  # BACK
    (4, 0, 6, 2),  # RIGHT
    (4, 5, 0, 1),  # BOTTOM (+Y; lower side on screen at default view)
    (7, 6, 3, 2),  # TOP    (-Y; upper side on screen at default view)
]

def cube_uv(u, v, w, h, d, mirrored=False, rotate_top=False):
    """Return Pillow-friendly UV *edge* coordinates for an Allumeria cube.
    cube.lua stores pixel-sampling coordinates, and its rasterizer applies a
    half-pixel V offset.  Translating those values literally into Pillow shifts
    the top/bottom strips by one pixel.  These coordinates describe the actual
    logical texel rectangles instead: top starts at (u+d, v), bottom at
    (u+d+w, v), and side strips start at y=v+d.
    """
    if mirrored:
        top_uv = [(u+d, v), (u+d+w, v), (u+d, v+d), (u+d+w, v+d)]
        if rotate_top:
            top_uv = [(u+d+w, v+d), (u+d, v+d), (u+d+w, v), (u+d, v)]
        return [
            [(u+d+w, v+d+h), (u+d, v+d+h), (u+d+w, v+d), (u+d, v+d)],
            [(u+d, v+d+h), (u, v+d+h), (u+d, v+d), (u, v+d)],
            [(u+2*d+2*w, v+d+h), (u+2*d+w, v+d+h), (u+2*d+2*w, v+d), (u+2*d+w, v+d)],
            [(u+2*d+w, v+d+h), (u+d+w, v+d+h), (u+2*d+w, v+d), (u+d+w, v+d)],
            [(u+d+2*w, v), (u+d+w, v), (u+d+2*w, v+d), (u+d+w, v+d)],
            top_uv
        ]
    top_uv = [(u+d+w, v), (u+d, v), (u+d+w, v+d), (u+d, v+d)]
    if rotate_top:
        top_uv = [(u+d, v+d), (u+d+w, v+d), (u+d, v), (u+d+w, v)]
    return [
        [(u+d, v+d+h), (u+d+w, v+d+h), (u+d, v+d), (u+d+w, v+d)],
        [(u+d+w, v+d+h), (u+2*d+w, v+d+h), (u+d+w, v+d), (u+2*d+w, v+d)],
        [(u+2*d+w, v+d+h), (u+2*d+2*w, v+d+h), (u+2*d+w, v+d), (u+2*d+2*w, v+d)],
        [(u, v+d+h), (u+d, v+d+h), (u, v+d), (u+d, v+d)],
        [(u+d+w, v), (u+d+2*w, v), (u+d+w, v+d), (u+d+2*w, v+d)],
        top_uv
    ]

class Mesh:
    def __init__(self, kind, center=(0,0,0), size=(1,1,1), uv=(0,0), inflate=0.0,
                 cull=True, mirrored=False, name='', rotate_top=False):
        self.kind = kind
        self.center = center
        self.size = size
        self.uv_origin = uv
        self.inflate = inflate
        self.cull = cull
        self.mirrored = mirrored
        self.name = name
        if kind == 'cube':
            self.vertices = self._cube_vertices()
            self.uv_faces = cube_uv(*uv, *size, mirrored=mirrored, rotate_top=rotate_top)
            self.faces = CUBE_FACES
        else:
            w, h = size[0] / 16.0, size[1] / 16.0
            self.vertices = [(-w, h, 0), (w, h, 0), (-w, -h, 0), (w, -h, 0)]
            u, v = uv
            pw, ph = size[0], size[1]
            if mirrored:
                self.uv_faces = [[(u + pw, v), (u, v), (u + pw, v + ph), (u, v + ph)]]
            else:
                self.uv_faces = [[(u, v), (u + pw, v), (u, v + ph), (u + pw, v + ph)]]
            self.faces = [(0,1,2,3)]

    def _cube_vertices(self):
        w, h, d = self.size
        inf = self.inflate * 2.0
        w = (w + inf) / 16.0
        h = (h + inf) / 16.0
        d = (d + inf) / 16.0
        cx, cy, cz = self.center
        cx, cy, cz = cx / 8.0, cy / 8.0, cz / 8.0
        return [
            (-w+cx,  h+cy, -d+cz), ( w+cx,  h+cy, -d+cz),
            (-w+cx, -h+cy, -d+cz), ( w+cx, -h+cy, -d+cz),
            (-w+cx,  h+cy,  d+cz), ( w+cx,  h+cy,  d+cz),
            (-w+cx, -h+cy,  d+cz), ( w+cx, -h+cy,  d+cz),
        ]

class Part:
    def __init__(self, pos=(0,0,0), rot=(0,0,0), meshes=(), name=''):
        self.pos = tuple(x/8.0 for x in pos)
        self.rot = rot
        self.meshes = list(meshes)
        self.name = name

    def world_vertex(self, p):
        return add(rot_xyz(p, *self.rot), self.pos)

def build_model():
    return [
        Part((1.5,12,0), meshes=[
            Mesh('cube',(-1.5,-24,0),(6,6,6),uv=(0,0),name='head'),
            Mesh('cube',(-1.5,-24.3,0),(7,7,7),uv=(0,30),inflate=-0.1,cull=False,name='hat'),
            Mesh('cube',(-1.5,-20.5,0),(4,1,3),uv=(0,26),name='neck'),
        ], name='head'),
        Part((0,-8.35061,-3.55061),rot=(0,0,math.radians(180)), meshes=[
            Mesh('plane',(0,0,0),(7,5,0),uv=(0,44),cull=False,name='beard'),
        ], name='beard'),
        Part((0,-16,0),rot=(0,0,math.radians(180)), meshes=[
            Mesh('plane',(0,0,0),(16,16,0),uv=(48,0),cull=False,name='hair_top'),
        ], name='hair_top'),
        Part((0,-7,3.061),rot=(math.radians(180),0,math.radians(-22.5)),meshes=[
            Mesh('plane',(0,0,0),(16,16,0),uv=(48,16),cull=False,name='hair_back')
        ],name='hair_back'),
        Part((0,0,5),rot=(0,math.radians(-90),0),meshes=[
            Mesh('plane',(0,0,0),(7,7,0),uv=(0,30),cull=False,name='tail')
        ],name='tail'),
        Part((0,-11.25,0),rot=(0,math.radians(90),math.radians(180)),meshes=[
            Mesh('plane',(0,0,0),(16,16,0),uv=(32,0),cull=False,name='hair_center')
        ],name='hair_center'),
        Part((0,9,0),meshes=[Mesh('cube',(0,-11.5,0),(6,11,3),uv=(0,12),name='torso')],name='torso'),
        Part((3,-2,0),meshes=[Mesh('cube',(1.5,0,0),(3,12,3),uv=(52,49),name='arm_r', rotate_top=True)],name='arm_r'),
        Part((-3,-2,0),meshes=[Mesh('cube',(-1.5,0,0),(3,12,3),uv=(40,49),name='arm_l', rotate_top=True)],name='arm_l'),
        Part((1.5,9,0),meshes=[Mesh('cube',(0,0,0),(3,12,3),uv=(12,49),name='leg_r')],name='leg_r'),
        Part((-1.5,9,0),meshes=[Mesh('cube',(0,0,0),(3,12,3),uv=(0,49),name='leg_l')],name='leg_l'),
    ]

# -----------------------------------------------------------------------------
# Perspective texture mapping
# -----------------------------------------------------------------------------
def solve8(rows, rhs):
    a = [list(r) + [b] for r,b in zip(rows,rhs)]
    n = 8
    for col in range(n):
        pivot = max(range(col,n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        q = a[col][col]
        for j in range(col,n+1): a[col][j] /= q
        for r in range(n):
            if r == col: continue
            q = a[r][col]
            if q:
                for j in range(col,n+1): a[r][j] -= q*a[col][j]
    return [a[i][n] for i in range(n)]

def perspective_coeff(dst, src):
    rows=[]; rhs=[]
    for (x,y),(u,v) in zip(dst,src):
        rows.append([x,y,1,0,0,0,-x*u,-y*u]); rhs.append(u)
        rows.append([0,0,0,x,y,1,-x*v,-y*v]); rhs.append(v)
    return solve8(rows,rhs)

def warp_face(texture, uv, dst, out_size):
    """Return a transparent RGBA patch for a perspective-mapped face."""
    W,H = out_size
    xs = [p[0] for p in dst]; ys = [p[1] for p in dst]
    x0 = max(0, int(math.floor(min(xs)) - 1)); y0 = max(0, int(math.floor(min(ys)) - 1))
    x1 = min(W, int(math.ceil(max(xs)) + 1)); y1 = min(H, int(math.ceil(max(ys)) + 1))
    if x1 <= x0 or y1 <= y0: return None, None
    local_dst = [(x-x0,y-y0) for x,y in dst]
    coeff = perspective_coeff(local_dst, uv)
    if coeff is None: return None, None
    patch = texture.transform((x1-x0,y1-y0), Image.Transform.PERSPECTIVE, coeff,
                              resample=Image.Resampling.NEAREST)
    mask = Image.new('L', (x1-x0,y1-y0), 0)
    md = ImageDraw.Draw(mask)
    md.polygon([local_dst[0], local_dst[1], local_dst[3], local_dst[2]], fill=255)
    patch.putalpha(Image.composite(patch.getchannel('A'), Image.new('L', patch.size, 0), mask))
    return patch, (x0,y0)

# -----------------------------------------------------------------------------
# Renderer
# -----------------------------------------------------------------------------
class Renderer:
    def __init__(self, texture, width=760, height=760):
        self.texture = texture.convert('RGBA')
        self.width = width
        self.height = height
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.zoom = 0.65
        self.fov = 30.0
        self.bg = (125,125,125,255)
        self.model = build_model()
        self.hidden_parts = set()

    def set_texture(self, texture):
        self.texture = texture.convert('RGBA')

    def camera_transform(self, p):
        p = camera_orbit(p, self.yaw, self.pitch)
        return (p[0], p[1], p[2] + 10.0 / self.zoom)

    def project(self, p):
        z = p[2]
        if z <= 0.03: return None
        f = 1.0 / math.tan(math.radians(self.fov)*0.5)
        aspect = self.height / self.width
        x = (p[0] * f * aspect / z) * self.height * 0.5 + self.width*0.5
        y = ((p[1] + 0.45) * f / z) * self.height*0.5 + self.height*0.52
        return (x,y)

    def render(self):
        frame = Image.new('RGBA', (self.width,self.height), self.bg)
        faces=[]
        tex_w, tex_h = self.texture.size
        scale = tex_w / 64.0
        if abs(tex_h/64.0-scale) > 1e-6:
            scale = min(tex_w,tex_h)/64.0
        for part in self.model:
            if part.name in self.hidden_parts:
                continue
            for mesh in part.meshes:
                verts_world = [part.world_vertex(v) for v in mesh.vertices]
                for fi, inds in enumerate(mesh.faces):
                    pts3 = [verts_world[i] for i in inds]
                    if mesh.kind == 'plane':
                        uv_base = mesh.uv_faces[0]
                        face_cull = False
                    else:
                        uv_base = mesh.uv_faces[fi]
                        face_cull = mesh.cull
                    uv = [(u*scale, v*scale) for u,v in uv_base]
                    cam = [self.camera_transform(p) for p in pts3]
                    normal = norm(cross(sub(cam[1],cam[0]), sub(cam[3],cam[0])))
                    if mesh.kind == 'cube' and normal[2] >= 0:
                        continue
                    if not all(p[2] > 0.03 for p in cam):
                        continue
                    dst = [self.project(p) for p in cam]
                    if any(p is None for p in dst): continue
                    depth = sum(p[2] for p in cam)/4.0
                    faces.append((depth, normal, uv, dst, not face_cull))
        faces.sort(key=lambda f: f[0], reverse=True)
        for depth, normal, uv, dst, double_sided in faces:
            patch, pos = warp_face(self.texture, uv, dst, frame.size)
            if patch is None: continue
            light = max(0.55, min(1.0, 0.72 + 0.28*abs(normal[2])))
            if light < 0.99:
                r,g,b,a = patch.split()
                r = r.point(lambda q: int(q*light))
                g = g.point(lambda q: int(q*light))
                b = b.point(lambda q: int(q*light))
                patch = Image.merge('RGBA',(r,g,b,a))
            frame.alpha_composite(patch, dest=pos)
        return frame

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
class App:
    def __init__(self, path, watch=False):
        self.path = Path(path).expanduser().resolve()
        self.watch = watch

        if _HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title(f'Allumeria Skin Viewer — {self.path.name}')
        self.root.geometry('820x880')
        self.root.resizable(width=False, height=False)
        self.root.minsize(520,600)
        self.root.configure(bg='#333333')

        try:
            texture = Image.open(self.path).convert('RGBA')
        except Exception as e:
            raise SystemExit(f'Could not open {self.path}: {e}')

        if texture.width != texture.height or texture.width < 64 or texture.width % 64:
            raise SystemExit('Allumeria texture must be square and 64×N pixels (64, 128, 256, ...).')

        self.renderer = Renderer(texture)
        self.photo = None
        self.last_mtime = self.path.stat().st_mtime_ns
        self.drag = None

        # --- Visibility toggle variables ---
        self.var_head  = tk.BooleanVar(value=True)
        self.var_torso = tk.BooleanVar(value=True)
        self.var_arms  = tk.BooleanVar(value=True)
        self.var_leg_r = tk.BooleanVar(value=True)
        self.var_leg_l = tk.BooleanVar(value=True)
        self.var_other = tk.BooleanVar(value=True)

        def update_visibility():
            self.renderer.hidden_parts = set()
            if not self.var_head.get():
                self.renderer.hidden_parts.add('head')
            if not self.var_torso.get():
                self.renderer.hidden_parts.add('torso')
            if not self.var_arms.get():
                self.renderer.hidden_parts.update({'arm_r', 'arm_l'})
            if not self.var_leg_r.get():
                self.renderer.hidden_parts.add('leg_r')
            if not self.var_leg_l.get():
                self.renderer.hidden_parts.add('leg_l')
            if not self.var_other.get():
                self.renderer.hidden_parts.update({
                    'beard', 'hair_top', 'hair_back', 'hair_center', 'tail'
                })
            self.render()

        # --- Top bar ---
        top = tk.Frame(self.root, bg='#333333')
        top.pack(fill='x', padx=8, pady=8)

        tk.Button(top, text='Refresh', command=self.refresh).pack(side='left')
        tk.Button(top, text='Reset view', command=self.reset).pack(side='left', padx=(6,0))

        tk.Label(top, text='|', fg='#666666', bg='#333333').pack(side='left', padx=(2,2))

        tk.Button(top, text='Front', command=lambda: self.view(0,0)).pack(side='left')
        tk.Button(top, text='Back',  command=lambda: self.view(math.pi,0)).pack(side='left')
        tk.Button(top, text='Left',  command=lambda: self.view(math.pi/2,0)).pack(side='left')
        tk.Button(top, text='Right', command=lambda: self.view(-math.pi/2,0)).pack(side='left')

        tk.Label(top, text='|', fg='#666666', bg='#333333').pack(side='left', padx=(2,2))

        # Visibility checkbuttons
        cb_style = {
            'bg': '#333333', 'fg': 'white', 'selectcolor': '#444444',
            'activebackground': '#333333', 'activeforeground': 'white',
            'highlightthickness': 0, 'bd': 0
        }

        tk.Checkbutton(top, text="Head",    variable=self.var_head,  command=update_visibility, **cb_style).pack(side='left', padx=(2,0))
        tk.Checkbutton(top, text="Torso",   variable=self.var_torso, command=update_visibility, **cb_style).pack(side='left', padx=(6,0))
        tk.Checkbutton(top, text="Arms",    variable=self.var_arms,  command=update_visibility, **cb_style).pack(side='left', padx=(6,0))
        tk.Checkbutton(top, text="R. Leg",  variable=self.var_leg_r, command=update_visibility, **cb_style).pack(side='left', padx=(6,0))
        tk.Checkbutton(top, text="L. Leg",  variable=self.var_leg_l, command=update_visibility, **cb_style).pack(side='left', padx=(6,0))
        tk.Checkbutton(top, text="Other",   variable=self.var_other, command=update_visibility, **cb_style).pack(side='left', padx=(6,0))

        self.status = tk.Label(top, text='', fg='white', bg='#333333', anchor='e')
        self.status.pack(side='right', fill='x', expand=True)

        # --- Canvas ---
        self.canvas = tk.Canvas(self.root, bg='#7d7d7d', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=8, pady=(0,8))

        # Drag-and-drop
        if _HAS_DND:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self.on_drop)

        self.canvas.bind('<Configure>', lambda e: self.render())
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.canvas.bind('<Button-4>', lambda e: self.zoom_by(1.08))
        self.canvas.bind('<Button-5>', lambda e: self.zoom_by(1/1.08))

        self.root.bind('<Key-r>', lambda e: self.refresh())
        self.root.bind('<Key-R>', lambda e: self.refresh())
        self.root.bind('<space>', lambda e: self.refresh())
        self.root.bind('<Key-f>', lambda e: self.reset())
        self.root.bind('<Escape>', lambda e: self.root.destroy())

        for key, ang in [('1',0),('2',-math.pi/2),('3',math.pi),('4',math.pi/2)]:
            self.root.bind(key, lambda e, a=ang: self.view(a,0))
        self.root.bind('5', lambda e: self.view(0, math.radians(89.0)))
        self.root.bind('6', lambda e: self.view(0,-math.radians(89.0)))

        self.render()
        self.poll()

    def on_drop(self, event):
        """Handle files dropped into the canvas."""
        try:
            files = self.root.splitlist(event.data)
            if files:
                file_path = files[0]
                if file_path.lower().endswith('.png'):
                    self.path = Path(file_path).expanduser().resolve()
                    self.root.title(f'Allumeria Skin Viewer — {self.path.name}')
                    self.refresh()
                else:
                    self.status.config(text='Dropped file is not a PNG')
        except Exception as e:
            self.status.config(text=f'Drop failed: {e}')

    def refresh(self):
        try:
            im = Image.open(self.path).convert('RGBA')
            if im.width != im.height or im.width < 64 or im.width % 64:
                raise ValueError('texture must be square and 64×N')
            self.renderer.set_texture(im)
            self.last_mtime = self.path.stat().st_mtime_ns
            self.status.config(text=f'{im.width}×{im.height} | refreshed')
            self.render()
        except Exception as e:
            self.status.config(text=f'Refresh failed: {e}')

    def poll(self):
        try:
            mt = self.path.stat().st_mtime_ns
            if mt != self.last_mtime:
                self.refresh()
        except OSError:
            pass
        self.root.after(400, self.poll)

    def render(self):
        w = max(200, self.canvas.winfo_width())
        h = max(200, self.canvas.winfo_height())
        self.renderer.width = w; self.renderer.height = h
        im = self.renderer.render()
        self.photo = ImageTk.PhotoImage(im)
        self.canvas.delete('all')
        self.canvas.create_image(w//2, h//2, image=self.photo)
        dnd_hint = " | drop PNG to change" if _HAS_DND else ""
        self.status.config(text=f'drag to rotate | wheel to zoom{dnd_hint}')

    def drag_start(self, e): self.drag = (e.x, e.y)
    def drag_move(self, e):
        if not self.drag: return
        ox, oy = self.drag
        self.renderer.yaw -= (e.x - ox) * 0.012
        self.renderer.pitch -= (e.y - oy) * 0.012
        limit = math.radians(89.5)
        self.renderer.pitch = max(-limit, min(limit, self.renderer.pitch))
        self.drag = (e.x, e.y)
        self.render()

    def wheel(self, e): self.zoom_by(1.10 if e.delta > 0 else 1/1.10)
    def zoom_by(self, f):
        self.renderer.zoom = max(0.35, min(3.0, self.renderer.zoom * f)); self.render()

    def reset(self):
        self.renderer.yaw = 0; self.renderer.pitch = 0; self.renderer.roll = 0; self.renderer.zoom = 0.65; self.render()

    def view(self, yaw, pitch):
        self.renderer.yaw = yaw; self.renderer.pitch = pitch; self.renderer.roll = 0; self.render()

    def run(self): self.root.mainloop()

def main():
    ap = argparse.ArgumentParser(description='Simple Allumeria 3D skin viewer')
    ap.add_argument('skin', nargs='?', help='Allumeria PNG skin')
    ap.add_argument('--watch', action='store_true', help='watch the PNG and refresh automatically (always polled lightly)')
    args = ap.parse_args()

    if not args.skin:
        root = tk.Tk(); root.withdraw()
        from tkinter import filedialog
        p = filedialog.askopenfilename(title='Open Allumeria skin', filetypes=[('PNG files','*.png'),('All files','*.*')])
        root.destroy()
        if not p: return
        args.skin = p

    App(args.skin, args.watch).run()

if __name__ == '__main__':
    main()