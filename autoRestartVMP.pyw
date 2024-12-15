import tkinter as tk
from tkinter import ttk  # Import the ttk module
from tkinter import PhotoImage
from ttkthemes import ThemedTk
import threading
import subprocess
import time
import pystray
from PIL import Image
import pygetwindow as gw
import os
from pywinauto.application import Application
import argparse

def main():
    # Start the Tkinter main loop in the main thread
    window = ThemedTk(theme="yaru")

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", help="start the countdown", action="store_true")
    parser.add_argument("-m", "--minimize", help="start minimized", action="store_true")
    args = parser.parse_args()

    # Create the App instance
    app = App(args, window)

    # Start the countdown if the -s/--start option was used
    if args.start:
        window.after(100, app.toggle)  # Delay the call to toggle

    # Minimize the window if the -m/--minimize option was used
    if args.minimize:
        window.after(100, app.minimize)  # Delay the call to minimize

    # Start the Tkinter main loop
    window.mainloop()


class App:
    # Initialization and main window setup
    def __init__(self, args, window):
        # Initialize the main window and variables
        self.window = window
        self.window.title("VoiceMeeter Restarter")
        self.countdown = 20 * 60  # Countdown time in seconds
        self.running = False  # Flag to indicate if the countdown is running

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.realpath(__file__))

        # Get the paths to the activated and deactivated images
        self.activated_image_path = os.path.join(script_dir, "activated.png")
        self.deactivated_image_path = os.path.join(script_dir, "deactivated.png")

        # Load the images
        self.activated_image = PhotoImage(file=self.activated_image_path)
        self.deactivated_image = PhotoImage(file=self.deactivated_image_path)

        # Create the indicator icon and pack it to the left
        self.indicator_icon = tk.Label(self.window, image=self.deactivated_image)
        self.indicator_icon.pack(side="left")

        # Create a frame to group the buttons and pack it to the right
        self.button_frame = tk.Frame(self.window)
        self.button_frame.pack(side="right")

        # Create the Start, Minimize, and Quit buttons and pack them into the frame
        self.start_button = ttk.Button(self.button_frame, text="Start", command=self.toggle)  # Use ttk.Button instead of tk.Button
        self.start_button.pack()

        self.minimize_button = ttk.Button(self.button_frame, text="Minimize to system tray", command=self.minimize)  # Use ttk.Button instead of tk.Button
        self.minimize_button.pack()

        self.restart_button = ttk.Button(self.button_frame, text="Manual Restart", command=self.manual_restart)  # Use ttk.Button instead of tk.Button
        self.restart_button.pack()

        self.quit_button = ttk.Button(self.button_frame, text="Quit", command=self.quit)  # Use ttk.Button instead of tk.Button
        self.quit_button.pack()

        # Create the countdown label and pack it
        self.countdown_label = ttk.Label(self.window, text="20:00")  # Use ttk.Label instead of tk.Label
        self.countdown_label.pack()

        # Set the window close event to minimize the window
        self.window.protocol("WM_DELETE_WINDOW", self.minimize)

        # Create the system tray icons for the running and paused states
        self.icon_running = pystray.Icon("name", Image.open(self.activated_image_path), "VoiceMeeter Restarter", menu=self.create_menu_running())
        self.icon_paused = pystray.Icon("name", Image.open(self.deactivated_image_path), "VoiceMeeter Restarter", menu=self.create_menu_paused())

        # Start with the paused icon
        self.icon = self.icon_paused

    # Button action methods
    def toggle(self):
        print("Toggle called")
        try:
            if self.running:
                self.running = False
                self.start_button.config(text="Start")
                if self.icon._running:  # Check if the icon is running
                    self.icon.stop()  # Stop the icon
                self.icon = pystray.Icon("name", Image.open(self.deactivated_image_path), "VoiceMeeter Restarter", menu=self.create_menu_paused())
                if not self.icon._running:  # Check if the icon is already running
                    threading.Thread(target=self.icon.run).start()  # Start the new icon
                self.indicator_icon.config(image=self.deactivated_image)  # Update the image in the main window
            else:
                self.running = True
                self.start_button.config(text="Pause")
                threading.Thread(target=self.run_countdown).start()  # Start the countdown thread
                if self.icon._running:  # Check if the icon is running
                    self.icon.stop()  # Stop the icon
                self.icon = pystray.Icon("name", Image.open(self.activated_image_path), "VoiceMeeter Restarter", menu=self.create_menu_running())
                if not self.icon._running:  # Check if the icon is already running
                    threading.Thread(target=self.icon.run).start()  # Start the new icon
                self.indicator_icon.config(image=self.activated_image)  # Update the image in the main window
        except Exception as e:
            print(f"Error in toggle: {e}")
    
    def manual_restart(self):
        # Manually restart the Voicemeeter application and reset the countdown
        self.restart_voicemeeter()
        self.countdown = 20 * 60
        self.countdown_label.config(text=self.format_time(self.countdown))

    def minimize(self):
        print("Minimize called")
        try:
            # Minimize the window and run the system tray icon
            self.window.withdraw()
            if not self.icon._running:
                threading.Thread(target=self.icon.run).start()
        except Exception as e:
            print(f"Error in minimize: {e}")

    def quit(self):
        # Stop the countdown and the system tray icon, then destroy the window after 1 second
        self.running = False
        if self.icon._running:
            self.icon.stop()
        self.window.after(1000, self.window.destroy)


    # Countdown related methods
    def run_countdown(self):
        # Run the countdown and update the countdown label every second
        while self.running and self.countdown > 0:
            self.countdown -= 1
            self.countdown_label.config(text=self.format_time(self.countdown))
            time.sleep(1)
        if self.countdown == 0:
            self.restart_voicemeeter()
            self.countdown = 20 * 60
            if self.running:
                threading.Thread(target=self.run_countdown).start()  # Restart the countdown thread

    def update_countdown(self):
        # Return the current countdown time in the MM:SS format
        return self.format_time(self.countdown)

    def format_time(self, seconds):
        # Format the given time in seconds as MM:SS
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    # System tray related methods
    def create_menu_running(self):
        # Create the system tray menu for the running state
        return (pystray.MenuItem("Open", lambda: self.window.after(0, self.window.deiconify)), 
                pystray.MenuItem("Pause", self.toggle),
                pystray.MenuItem("Manual Restart", self.manual_restart),
                pystray.MenuItem(lambda text: f"Countdown: {self.update_countdown()} (click me)", self.update_countdown),
                pystray.MenuItem("Quit", self.quit))

    def create_menu_paused(self):
        # Create the system tray menu for the paused state
        return (pystray.MenuItem("Open", lambda: self.window.after(0, self.window.deiconify)), 
                pystray.MenuItem("Resume", self.toggle),
                pystray.MenuItem("Manual Restart", self.manual_restart),
                pystray.MenuItem(lambda text: f"Countdown: {self.update_countdown()} (click me)", self.update_countdown),
                pystray.MenuItem("Quit", self.quit))

    def update_icon(self, new_icon):
        # Stop the current icon if it's running
        if self.icon._running:
            self.icon.stop()
            # Wait for the icon to actually stop
            while self.icon._running:
                time.sleep(0.1)

        # Start the new icon if it's not already running
        self.icon = new_icon
        if not self.icon._running:
            threading.Thread(target=self.icon.run).start()

    from pywinauto.application import Application

    def restart_voicemeeter(self):
        # Restart the Voicemeeter application and minimize its window
        subprocess.run(["C:\\Program Files (x86)\\VB\\Voicemeeter\\voicemeeter8x64.exe", "-R"])
        time.sleep(2)
        try:
            app = Application().connect(title_re="Voicemeeter")
            if not app.Voicemeeter.is_minimized():  # Check if the window is minimized
                app.Voicemeeter.minimize()  # Minimize the window if it's not already minimized
        except Exception as e:
            print(f"Error minimizing Voicemeeter window: {e}")

if __name__ == "__main__":
    main()