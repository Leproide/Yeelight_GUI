import tkinter as tk
from tkinter import messagebox, colorchooser
from yeelight import Bulb
from PIL import Image, ImageTk
import math
import xml.etree.ElementTree as ET
import os
import threading

CONFIG_FILE = "lights_config.xml"

class YeelightManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yeelight Manager")
        self.geometry("850x650")
        self.resizable(True, True)

        self.configure(bg="#2E2E2E")  # Dark background for the window

        self.initialized = False
        self.devices = []
        self.load_config()

        container = tk.Frame(self, bg="#2E2E2E")  # Container background
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel (devices)
        frame_devices = tk.Frame(container, bd=2, relief=tk.GROOVE, bg="#3A3A3A")  # Dark grey panel
        frame_devices.grid(row=0, column=0, sticky="ns", padx=5, pady=5)

        tk.Label(frame_devices, text="Devices", fg="white", bg="#3A3A3A").pack(pady=(10, 0))  # White text
        self.listbox = tk.Listbox(frame_devices, width=30, height=20, bg="#3A3A3A", fg="white", selectbackground="#555", selectforeground="white")
        self.listbox.pack(pady=5, padx=5)

        tk.Label(frame_devices, text="Name:", fg="white", bg="#3A3A3A").pack(anchor=tk.W, padx=5)
        self.entry_name = tk.Entry(frame_devices, width=25, bg="#555", fg="white")
        self.entry_name.pack(pady=2, padx=5)

        tk.Label(frame_devices, text="IP:", fg="white", bg="#3A3A3A").pack(anchor=tk.W, padx=5)
        self.entry_ip = tk.Entry(frame_devices, width=25, bg="#555", fg="white")
        self.entry_ip.pack(pady=2, padx=5)

        btn_add = tk.Button(frame_devices, text="Add", width=20, command=self.add_device, bg="#444", fg="white")
        btn_add.pack(pady=5)
        btn_remove = tk.Button(frame_devices, text="Remove", width=20, command=self.remove_device, bg="#444", fg="white")
        btn_remove.pack(pady=5)

        if self.devices:
            for device in self.devices:
                self.listbox.insert(tk.END, f"{device['name']} ({device['ip']})")
            self.listbox.select_set(0)

        # Right panel (controls)
        frame_controls = tk.Frame(container, bd=2, relief=tk.GROOVE, bg="#3A3A3A")  # Dark grey panel
        frame_controls.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        container.columnconfigure(1, weight=1)

        frame_mode = tk.Frame(frame_controls, bg="#3A3A3A")
        frame_mode.pack(pady=10)

        btn_night = tk.Button(frame_mode, text="Night Mode", width=20, command=self.night_mode, bg="#444", fg="white")
        btn_night.pack(side=tk.LEFT, padx=5)

        btn_day = tk.Button(frame_mode, text="Day Mode", width=20, command=self.day_mode, bg="#444", fg="white")
        btn_day.pack(side=tk.LEFT, padx=5)

        btn_toggle = tk.Button(frame_mode, text="Toggle On/Off", width=20, command=self.toggle_light, bg="#444", fg="white")
        btn_toggle.pack(side=tk.LEFT, padx=5)

        # Sliders
        self.temp_slider = tk.Scale(frame_controls, from_=1700, to=6500, orient=tk.HORIZONTAL,
                                    label="Color Temperature", length=400, bg="#3A3A3A", fg="white", troughcolor="#555")
        self.temp_slider.set(4000)
        self.temp_slider.pack(pady=10)
        self.temp_slider.bind('<ButtonRelease-1>', self.on_temp_slider_release)

        self.brightness_slider = tk.Scale(frame_controls, from_=1, to=100, orient=tk.HORIZONTAL,
                                          label="Brightness", length=400, bg="#3A3A3A", fg="white", troughcolor="#555")
        self.brightness_slider.set(50)
        self.brightness_slider.pack(pady=10)
        self.brightness_slider.bind('<ButtonRelease-1>', self.on_brightness_slider_release)

        btn_color = tk.Button(frame_controls, text="Choose Color (dialog)", width=25, command=self.choose_color, bg="#444", fg="white")
        btn_color.pack(pady=10)

        self.wheel_size = 300
        self.color_wheel = self.create_color_wheel(self.wheel_size)
        self.wheel_photo = ImageTk.PhotoImage(self.color_wheel)
        self.canvas = tk.Canvas(frame_controls, width=self.wheel_size, height=self.wheel_size,
                               bd=0, highlightthickness=0)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.wheel_photo)
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.wheel_click)

        self.initialized = True

    def on_temp_slider_release(self, event):
        if not self.initialized:
            return
        self.set_color_temp(self.temp_slider.get())

    def on_brightness_slider_release(self, event):
        if not self.initialized:
            return
        self.set_brightness(self.brightness_slider.get())

    def set_color_temp(self, temp):
        bulb = self.get_current_bulb()
        if bulb:
            try:
                def cmd():
                    bulb.turn_on()
                    bulb.set_color_temp(temp)
                self.execute_bulb_command(cmd)
            except Exception as e:
                messagebox.showerror("Error", f"Temperature setting error: {e}")

    def set_brightness(self, brightness):
        bulb = self.get_current_bulb()
        if bulb:
            try:
                def cmd():
                    bulb.turn_on()
                    bulb.set_brightness(brightness)
                self.execute_bulb_command(cmd)
            except Exception as e:
                messagebox.showerror("Error", f"Brightness setting error: {e}")

    def night_mode(self):
        if not self.initialized:
            return
        bulb = self.get_current_bulb()
        if bulb:
            def cmd():
                bulb.send_command("set_power", ["on", "smooth", 500, 5])
            self.execute_bulb_command(cmd)
            self.temp_slider.set(2700)
            self.brightness_slider.set(30)

    def day_mode(self):
        if not self.initialized:
            return
        bulb = self.get_current_bulb()
        if bulb:
            def cmd():
                bulb.turn_on()
                bulb.set_color_temp(6500)
                bulb.set_brightness(100)
            self.execute_bulb_command(cmd)
            self.temp_slider.set(6500)
            self.brightness_slider.set(100)

    def add_device(self):
        name = self.entry_name.get().strip()
        ip = self.entry_ip.get().strip()
        if name and ip:
            device = {"name": name, "ip": ip}
            self.devices.append(device)
            self.listbox.insert(tk.END, f"{name} ({ip})")
            self.entry_name.delete(0, tk.END)
            self.entry_ip.delete(0, tk.END)
            self.save_config()
        else:
            messagebox.showerror("Error", "Name and IP are required.")

    def remove_device(self):
        try:
            index = self.listbox.curselection()[0]
            self.listbox.delete(index)
            del self.devices[index]
            self.save_config()
        except IndexError:
            messagebox.showerror("Error", "Select a device to remove")

    def get_current_bulb(self):
        if not self.devices:
            messagebox.showerror("Error", "No saved devices!")
            return None
        selection = self.listbox.curselection()
        if not selection:
            self.listbox.select_set(0)
            selection = (0,)
        index = selection[0]
        device = self.devices[index]
        return Bulb(device["ip"])

    def execute_bulb_command(self, command, *args, **kwargs):
        def task():
            try:
                command(*args, **kwargs)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", 
                        "Device communication error: " + str(e)))
        t = threading.Thread(target=task, daemon=True)
        t.start()
        self.after(5000, lambda: self.check_thread(t))

    def check_thread(self, t):
        if t.is_alive():
            messagebox.showerror("Error", "Timeout: Command took too long")

    def toggle_light(self):
        if not self.initialized:
            return
        bulb = self.get_current_bulb()
        if bulb:
            self.execute_bulb_command(bulb.toggle)

    def choose_color(self):
        if not self.initialized:
            return
        color_code = colorchooser.askcolor(title="Choose Color")
        if color_code:
            rgb, _ = color_code
            if rgb:
                r, g, b = map(int, rgb)
                bulb = self.get_current_bulb()
                if bulb:
                    def cmd():
                        bulb.turn_on()
                        bulb.set_rgb(r, g, b)
                    self.execute_bulb_command(cmd)

    def create_color_wheel(self, size):
        image = Image.new("RGB", (size, size))
        center = size / 2
        for x in range(size):
            for y in range(size):
                dx = x - center
                dy = y - center
                distance = math.sqrt(dx*dx + dy*dy)
                if distance <= center:
                    angle = math.degrees(math.atan2(dy, dx))
                    if angle < 0:
                        angle += 360
                    hue = angle / 360.0
                    saturation = distance / center
                    r, g, b = self.hsv_to_rgb(hue, saturation, 1)
                    image.putpixel((x, y), (int(r*255), int(g*255), int(b*255)))
                else:
                    image.putpixel((x, y), (58, 58, 58))
        return image

    def hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return (v, v, v)
        i = int(h * 6)
        f = (h * 6) - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        i = i % 6
        if i == 0:
            return (v, t, p)
        if i == 1:
            return (q, v, p)
        if i == 2:
            return (p, v, t)
        if i == 3:
            return (p, q, v)
        if i == 4:
            return (t, p, v)
        if i == 5:
            return (v, p, q)

    def wheel_click(self, event):
        if not self.initialized:
            return
        x = event.x
        y = event.y
        center = self.wheel_size / 2
        dx = x - center
        dy = y - center
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > center:
            return
        rgb = self.color_wheel.getpixel((x, y))
        bulb = self.get_current_bulb()
        if bulb:
            def cmd():
                bulb.turn_on()
                bulb.set_rgb(*rgb)
            self.execute_bulb_command(cmd)

    def save_config(self):
        root = ET.Element("devices")
        for dev in self.devices:
            device_el = ET.SubElement(root, "device")
            name_el = ET.SubElement(device_el, "name")
            name_el.text = dev["name"]
            ip_el = ET.SubElement(device_el, "ip")
            ip_el.text = dev["ip"]
        tree = ET.ElementTree(root)
        try:
            tree.write(CONFIG_FILE, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            messagebox.showerror("Error", f"Config save error: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            tree = ET.parse(CONFIG_FILE)
            root = tree.getroot()
            for device_el in root.findall("device"):
                name = device_el.find("name").text
                ip = device_el.find("ip").text
                self.devices.append({"name": name, "ip": ip})
        except Exception as e:
            messagebox.showerror("Error", f"Config load error: {e}")

if __name__ == "__main__":
    app = YeelightManager()
    app.mainloop()