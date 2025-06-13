import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import io

class PDFEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Eraser Tool")

        # Help button on top
        help_frame = tk.Frame(self.root)
        help_frame.pack(fill=tk.X)
        tk.Button(help_frame, text="Help", command=self.show_help).pack(side=tk.RIGHT, padx=5, pady=3)

        self.canvas = tk.Canvas(root, cursor="cross", bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._setup_buttons()
        self._setup_bindings()

        self.doc = None
        self.page = None
        self.page_index = 0
        self.tk_img = None
        self.image_id = None

        self.scale = 2.0
        self.scale_step = 0.25
        self.min_scale = 1.0
        self.max_scale = 5.0

        self.start_x = self.start_y = 0
        self.rect = None
        self.erasures = []  # list of (x0, y0, x1, y1)

        self.selection_rects = []  # To show selection rectangles on canvas (red border)

    def show_help(self):
        help_text = (
            "Keyboard Shortcuts:\n"
            "-------------------\n"
            "Up / Down Arrow: Navigate previous / next page\n"
            "Enter: Apply erase to selected area(s)\n"
            "Ctrl + S: Save PDF\n"
            "Mouse Wheel: Zoom In / Zoom Out\n"
            "\n"
            "Use mouse drag to select area to erase.\n"
            "Unselect Latest: Removes last selection before apply.\n"
            "Unselect All: Clears all selections before apply.\n"
        )
        messagebox.showinfo("Help - Keyboard Shortcuts", help_text)

    def _setup_buttons(self):
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X)

        tk.Button(btn_frame, text="Load PDF", command=self.load_pdf).pack(side=tk.LEFT)

        self.prev_btn = tk.Button(btn_frame, text="Previous Page", command=self.prev_page, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT)
        self.next_btn = tk.Button(btn_frame, text="Next Page", command=self.next_page, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT)

        self.apply_btn = tk.Button(btn_frame, text="Apply", command=self.apply_erasure, state=tk.DISABLED)
        self.apply_btn.pack(side=tk.LEFT)
        self.save_btn = tk.Button(btn_frame, text="Save PDF", command=self.save_pdf, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT)

        tk.Button(btn_frame, text="Unselect Latest", command=self.unselect_latest, state=tk.DISABLED).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Unselect All", command=self.unselect_all, state=tk.DISABLED).pack(side=tk.LEFT)

        tk.Button(btn_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.RIGHT)

    def _setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.root.bind("<Return>", self.apply_erasure_event)
        self.root.bind("<Control-s>", self.save_pdf_event)
        self.root.bind("<Up>", self.prev_page_event)
        self.root.bind("<Down>", self.next_page_event)

        # Bind arrow keys also on canvas to capture when canvas has focus
        self.canvas.bind("<Up>", self.prev_page_event)
        self.canvas.bind("<Down>", self.next_page_event)

    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        self.doc = fitz.open(path)
        self.page_index = 0
        self.page = self.doc[self.page_index]
        self.erasures.clear()
        self.clear_selection_rects()

        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.doc.page_count > 1 else tk.DISABLED)
        self.update_unselect_buttons()

        self.render_page()

    def render_page(self):
        matrix = fitz.Matrix(self.scale, self.scale)
        pix = self.page.get_pixmap(matrix=matrix)
        img = Image.open(io.BytesIO(pix.tobytes("ppm")))
        self.tk_img = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.image_id = self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")

        # Draw current selection rectangles (red outlines)
        for x0, y0, x1, y1 in self.erasures:
            r = self.canvas.create_rectangle(x0, y0, x1, y1, outline="red", width=2)
            self.selection_rects.append(r)

        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.canvas.config(width=self.tk_img.width(), height=self.tk_img.height())

    def clear_selection_rects(self):
        for r in self.selection_rects:
            self.canvas.delete(r)
        self.selection_rects.clear()

    def prev_page(self):
        if self.doc and self.page_index > 0:
            self.page_index -= 1
            self.page = self.doc[self.page_index]
            self.erasures.clear()
            self.clear_selection_rects()
            self.render_page()
            self.update_nav_buttons()
            self.update_unselect_buttons()

    def next_page(self):
        if self.doc and self.page_index < self.doc.page_count - 1:
            self.page_index += 1
            self.page = self.doc[self.page_index]
            self.erasures.clear()
            self.clear_selection_rects()
            self.render_page()
            self.update_nav_buttons()
            self.update_unselect_buttons()

    def update_nav_buttons(self):
        self.prev_btn.config(state=tk.NORMAL if self.page_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.page_index < self.doc.page_count - 1 else tk.DISABLED)

    def update_unselect_buttons(self):
        state = tk.NORMAL if self.erasures else tk.DISABLED
        for btn_text in ["Unselect Latest", "Unselect All"]:
            # Find button by text and update state
            for widget in self.root.pack_slaves():
                if isinstance(widget, tk.Frame):
                    for b in widget.pack_slaves():
                        if isinstance(b, tk.Button) and b.cget("text") == btn_text:
                            b.config(state=state)

    def on_start(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red")

    def on_drag(self, event):
        if self.rect:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        if self.rect:
            x0, y0 = self.start_x, self.start_y
            x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.erasures.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

            # Keep the rectangle visible
            self.selection_rects.append(self.rect)
            self.rect = None

            self.update_unselect_buttons()

    def apply_erasure(self):
        if not self.erasures:
            messagebox.showinfo("No Selection", "No area selected to erase.")
            return

        for x0, y0, x1, y1 in self.erasures:
            pdf_x0 = x0 / self.scale
            pdf_y0 = y0 / self.scale
            pdf_x1 = x1 / self.scale
            pdf_y1 = y1 / self.scale
            rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            self.page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
        self.erasures.clear()
        self.clear_selection_rects()
        self.render_page()
        self.update_unselect_buttons()

    def save_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.doc.save(path)

    def zoom_in(self):
        if self.scale + self.scale_step <= self.max_scale:
            self.scale += self.scale_step
            self.render_page()

    def zoom_out(self):
        if self.scale - self.scale_step >= self.min_scale:
            self.scale -= self.scale_step
            self.render_page()

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def apply_erasure_event(self, event):
        self.apply_erasure()

    def save_pdf_event(self, event):
        self.save_pdf()

    def prev_page_event(self, event):
        self.prev_page()

    def next_page_event(self, event):
        self.next_page()

    def unselect_latest(self):
        if self.erasures:
            self.erasures.pop()
            # Remove the last rectangle from canvas
            if self.selection_rects:
                r = self.selection_rects.pop()
                self.canvas.delete(r)
            self.update_unselect_buttons()

    def unselect_all(self):
        self.erasures.clear()
        self.clear_selection_rects()
        self.update_unselect_buttons()

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditorApp(root)
    root.mainloop()
