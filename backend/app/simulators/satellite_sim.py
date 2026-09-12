import numpy as np
import scipy.ndimage as ndimage
import matplotlib.pyplot as plt
from PIL import Image
import io
import math

class SatelliteSimulator:
    def __init__(self, width=512, height=512, seed=42):
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        
        # Mine bounds
        self.south = 21.5400
        self.west = 79.6700
        self.north = 21.5600
        self.east = 79.6967

        # Center pixel
        self.cx = self.width // 2
        self.cy = self.height // 2
        self.pit_radius = int(self.width * 0.28)
        
        self.x_grid, self.y_grid = np.meshgrid(np.arange(self.width), np.arange(self.height))
        self.dist_from_center = np.sqrt((self.x_grid - self.cx)**2 + (self.y_grid - self.cy)**2)
        
        # Fault line mask (NE-SW trend)
        self.fault_mask = np.abs((self.x_grid - self.cx) - (self.y_grid - self.cy) * 0.8) < 20

    def _generate_grf(self, sigma_macro=32, sigma_micro=8):
        noise = self.rng.normal(0, 1, (self.height, self.width))
        macro = ndimage.gaussian_filter(noise, sigma=sigma_macro)
        micro = ndimage.gaussian_filter(self.rng.normal(0, 1, (self.height, self.width)), sigma=sigma_micro)
        combined = macro + 0.3 * micro
        return (combined - combined.min()) / (combined.max() - combined.min())

    def _array_to_png_bytes(self, array, cmap_name, vmin, vmax):
        norm_array = np.clip((array - vmin) / (vmax - vmin), 0, 1)
        cmap = plt.get_cmap(cmap_name)
        rgba = cmap(norm_array)
        
        # Areas outside mine area slightly transparent
        alpha_mask = np.where(self.dist_from_center > self.pit_radius * 1.5, 200, 255)
        rgba[:, :, 3] = alpha_mask / 255.0
        
        img = Image.fromarray((rgba * 255).astype(np.uint8), 'RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    def generate_all_layers(self) -> dict[str, bytes]:
        return {
            'ndvi': self.get_layer_png('ndvi'),
            'iron_oxide': self.get_layer_png('iron_oxide'),
            'clay_alteration': self.get_layer_png('clay_alteration'),
            'magnetics': self.get_layer_png('magnetics'),
            'gravity': self.get_layer_png('gravity')
        }

    def get_layer_png(self, layer_name: str) -> bytes:
        grf = self._generate_grf()
        
        if layer_name == 'ndvi':
            base = 0.68 + grf * 0.17 # Forest
            
            # Pit floor
            pit_mask = self.dist_from_center < self.pit_radius
            base = np.where(pit_mask, self.rng.uniform(-0.08, 0.12, (self.height, self.width)), base)
            
            # Waste dump area
            dump_dist = np.sqrt((self.x_grid - (self.cx - 80))**2 + (self.y_grid - (self.cy + 100))**2)
            dump_mask = dump_dist < self.pit_radius * 0.6
            base = np.where(dump_mask & ~pit_mask, self.rng.uniform(0.05, 0.18, (self.height, self.width)), base)
            
            # Stress perimeter
            stress_mask = (self.dist_from_center >= self.pit_radius) & (self.dist_from_center < self.pit_radius * 1.3)
            base = np.where(stress_mask & ~dump_mask, self.rng.uniform(0.20, 0.38, (self.height, self.width)), base)
            
            return self._array_to_png_bytes(base, 'RdYlGn', -0.1, 0.9)
            
        elif layer_name == 'iron_oxide':
            base = 0.8 + grf * 0.3
            pit_mask = self.dist_from_center < self.pit_radius
            gossan = np.where(pit_mask | self.fault_mask, self.rng.uniform(1.3, 2.2, (self.height, self.width)), base)
            gossan = ndimage.gaussian_filter(gossan, sigma=3)
            return self._array_to_png_bytes(gossan, 'hot', 0.8, 2.2)
            
        elif layer_name == 'clay_alteration':
            base = 0.9 + grf * 0.25
            halo = np.where(self.fault_mask, self.rng.uniform(1.25, 1.85, (self.height, self.width)), base)
            halo = ndimage.gaussian_filter(halo, sigma=6)
            return self._array_to_png_bytes(halo, 'coolwarm', 0.9, 1.85)
            
        elif layer_name == 'magnetics':
            base = self._generate_grf(sigma_macro=64, sigma_micro=16) * 100 - 50
            bif_anomaly = np.exp(-((self.x_grid - self.cx)**2 + (self.y_grid - self.cy + 50)**2) / 10000) * 150
            total_mag = base + bif_anomaly
            return self._array_to_png_bytes(total_mag, 'seismic', -50, 150)
            
        elif layer_name == 'gravity':
            base = self._generate_grf(sigma_macro=48, sigma_micro=12) * 5 - 2.5
            ore_anomaly = np.exp(-(self.dist_from_center**2) / 8000) * 8.0
            total_grav = base + ore_anomaly
            return self._array_to_png_bytes(total_grav, 'viridis', -3, 9)
            
        else:
            raise ValueError(f"Unknown layer {layer_name}")

    def get_bounds(self) -> dict:
        return {
            'south': self.south,
            'west': self.west,
            'north': self.north,
            'east': self.east
        }
