import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import queue

class TKMonitorPanel:
    def __init__(self, master, font_size=12):
        self.master = master
        master.title("Variable Monitor")

        self.custom_font = tkfont.Font(family="Helvetica", size=font_size)

        self.frame = ttk.Frame(master, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.labels = []
        self.values = []

        for i in range(6):
            label = ttk.Label(self.frame, text=f"Variable {i+1}:", font=self.custom_font)
            label.grid(row=i, column=0, sticky=tk.W, pady=5)
            self.labels.append(label)

            value = ttk.Label(self.frame, text="N/A", font=self.custom_font)
            value.grid(row=i, column=1, sticky=tk.W, pady=5)
            self.values.append(value)

        self.update_queue = queue.Queue()
        self.font_size_queue = queue.Queue()
        self.check_queue()

    def update(self, var1, var2, var3, var4, var5, var6):
        self.update_queue.put((var1, var2, var3, var4, var5, var6))

    def check_queue(self):
        try:
            while True:
                variables = self.update_queue.get_nowait()
                for i, var in enumerate(variables):
                    self.values[i].config(text=str(var))
        except queue.Empty:
            pass

        try:
            while True:
                new_size = self.font_size_queue.get_nowait()
                self.custom_font.configure(size=new_size)
                # Resize window to fit new font size
                self.master.update_idletasks()
                self.master.geometry('')
        except queue.Empty:
            pass

        self.master.after(100, self.check_queue)

    def set_font_size(self, size):
        self.font_size_queue.put(size)