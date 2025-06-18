from firestore_module import SupabaseMDXManager
import tkinter as tk

# Entry point for BlogDesktopApp

def main():
    root = tk.Tk()
    app = SupabaseMDXManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
