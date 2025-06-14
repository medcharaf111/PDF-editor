import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
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

        # Create a frame to hold the canvas and scrollbars
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create scrollbars
        self.v_scrollbar = tk.Scrollbar(self.canvas_frame)
        self.h_scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self.canvas_frame, cursor="cross", bg="gray",
                              yscrollcommand=self.v_scrollbar.set,
                              xscrollcommand=self.h_scrollbar.set)
        
        # Configure scrollbars
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        
        # Pack scrollbars and canvas
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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
        self.text_annotations = []  # list of (x, y, text, text_id, font_size)
        self.selected_text_index = -1  # Index of selected text annotation
        self.current_font_size = 12  # Default font size
        self.dragging_text = False  # Flag to track if we're dragging text
        self.drag_start_x = 0  # Starting X position for drag
        self.drag_start_y = 0  # Starting Y position for drag
        self.remove_text_mode = False  # Flag to track if we're in text removal mode

        self.selection_rects = []  # To show selection rectangles on canvas (red border)
        self.text_mode = False  # Flag to track if we're in text addition mode

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
            "\n"
            "Text Mode:\n"
            "Click 'Add Text' to enter text mode.\n"
            "Click anywhere on the PDF to add text.\n"
            "Click 'Add Text' again to exit text mode.\n"
            "Left-click on existing text to change its font size.\n"
            "Right-click and drag to move text to a new position.\n"
            "Use the font size selector to change text size for new text.\n"
            "Click 'Apply' to save text changes to the page.\n"
            "\n"
            "Text Removal:\n"
            "Click 'Remove Text' to enter removal mode.\n"
            "Click on any text to remove it.\n"
            "Click 'Remove Text' again to exit removal mode."
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

        self.text_btn = tk.Button(btn_frame, text="Add Text", command=self.toggle_text_mode, state=tk.DISABLED)
        self.text_btn.pack(side=tk.LEFT)

        self.remove_text_btn = tk.Button(btn_frame, text="Remove Text", command=self.toggle_remove_text_mode, state=tk.DISABLED)
        self.remove_text_btn.pack(side=tk.LEFT)

        # Add font size selector
        tk.Label(btn_frame, text="Font Size:").pack(side=tk.LEFT, padx=(10, 0))
        self.font_size_var = tk.StringVar(value="12")
        font_sizes = ["8", "10", "12", "14", "16", "18", "20", "24", "28", "32"]
        self.font_size_combo = ttk.Combobox(btn_frame, textvariable=self.font_size_var, 
                                          values=font_sizes, width=5, state="readonly")
        self.font_size_combo.pack(side=tk.LEFT)
        self.font_size_combo.bind("<<ComboboxSelected>>", self.on_font_size_change)

        tk.Button(btn_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.RIGHT)

    def toggle_remove_text_mode(self):
        if self.text_mode:
            self.toggle_text_mode()  # Turn off text mode first
        
        self.remove_text_mode = not self.remove_text_mode
        if self.remove_text_mode:
            self.remove_text_btn.config(relief=tk.SUNKEN)
            self.canvas.config(cursor="crosshair")
            self.text_btn.config(state=tk.NORMAL, relief=tk.RAISED)
            self.font_size_combo.config(state="disabled")
        else:
            self.remove_text_btn.config(relief=tk.RAISED)
            self.canvas.config(cursor="cross")
            self.text_btn.config(state=tk.NORMAL)
        self.render_page()

    def on_font_size_change(self, event=None):
        try:
            self.current_font_size = int(self.font_size_var.get())
            if self.text_mode:
                self.render_page()
        except ValueError:
            pass

    def toggle_text_mode(self):
        if self.remove_text_mode:
            self.toggle_remove_text_mode()  # Turn off remove mode first
        
        self.text_mode = not self.text_mode
        if self.text_mode:
            self.text_btn.config(relief=tk.SUNKEN)
            self.canvas.config(cursor="crosshair")
            self.font_size_combo.config(state="readonly")
            self.remove_text_btn.config(state=tk.NORMAL, relief=tk.RAISED)
        else:
            self.text_btn.config(relief=tk.RAISED)
            self.canvas.config(cursor="cross")
            self.font_size_combo.config(state="disabled")
            self.selected_text_index = -1
            self.dragging_text = False
            self.render_page()

    def _setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>", self.on_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_start)  # Right mouse button
        self.canvas.bind("<B3-Motion>", self.on_right_drag)       # Right mouse drag
        self.canvas.bind("<ButtonRelease-3>", self.on_right_release)  # Right mouse release
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.root.bind("<Return>", self.apply_erasure_event)
        self.root.bind("<Control-s>", self.save_pdf_event)
        self.root.bind("<Up>", self.prev_page_event)
        self.root.bind("<Down>", self.next_page_event)

        # Bind arrow keys also on canvas to capture when canvas has focus
        self.canvas.bind("<Up>", self.prev_page_event)
        self.canvas.bind("<Down>", self.next_page_event)

    def on_start(self, event):
        if self.remove_text_mode:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Check if clicked on existing text
            for i, (tx, ty, text, _, font_size) in enumerate(self.text_annotations):
                # Create a temporary text item to get its bbox
                temp_text = self.canvas.create_text(tx, ty, text=text, anchor="nw", font=("Arial", font_size))
                bbox = self.canvas.bbox(temp_text)
                self.canvas.delete(temp_text)
                
                if bbox and x >= bbox[0] and x <= bbox[2] and y >= bbox[1] and y <= bbox[3]:
                    # Remove the clicked text
                    self.text_annotations.pop(i)
                    self.render_page()
                    return
            return

        if self.text_mode:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Check if clicked on existing text
            for i, (tx, ty, text, _, font_size) in enumerate(self.text_annotations):
                # Create a temporary text item to get its bbox
                temp_text = self.canvas.create_text(tx, ty, text=text, anchor="nw", font=("Arial", font_size))
                bbox = self.canvas.bbox(temp_text)
                self.canvas.delete(temp_text)
                
                if bbox and x >= bbox[0] and x <= bbox[2] and y >= bbox[1] and y <= bbox[3]:
                    # Ask for new font size
                    new_size = simpledialog.askinteger("Change Font Size", 
                                                     "Enter new font size:",
                                                     initialvalue=font_size,
                                                     minvalue=8,
                                                     maxvalue=72)
                    if new_size:
                        # Update the font size
                        self.text_annotations[i] = (tx, ty, text, None, new_size)
                        self.font_size_var.set(str(new_size))  # Update the font size selector
                        self.current_font_size = new_size
                        self.render_page()
                    return
            
            # If not clicked on existing text, add new text
            text = simpledialog.askstring("Add Text", "Enter text to add:")
            if text:
                text_id = self.canvas.create_text(x, y, text=text, fill="black", anchor="nw", 
                                                font=("Arial", self.current_font_size))
                self.text_annotations.append((x, y, text, text_id, self.current_font_size))
                self.render_page()
            return

        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red")

    def on_drag(self, event):
        if self.text_mode and self.dragging_text and self.selected_text_index >= 0:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Calculate new position
            new_x = x - self.drag_start_x
            new_y = y - self.drag_start_y
            
            # Update the text position in the annotations list
            x, y, text, _, font_size = self.text_annotations[self.selected_text_index]
            self.text_annotations[self.selected_text_index] = (new_x, new_y, text, _, font_size)
            
            # Redraw the page to show the new position
            self.render_page()
            return

        if self.rect:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        if self.text_mode and self.dragging_text:
            self.dragging_text = False
            self.selected_text_index = -1
            self.canvas.config(cursor="crosshair")
            return

        if self.rect:
            x0, y0 = self.start_x, self.start_y
            x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            self.erasures.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

            # Keep the rectangle visible
            self.selection_rects.append(self.rect)
            self.rect = None

            self.update_unselect_buttons()

    def apply_erasure(self):
        if not self.erasures and not self.text_annotations:
            messagebox.showinfo("No Changes", "No changes to apply.")
            return

        # Apply erasures
        for x0, y0, x1, y1 in self.erasures:
            pdf_x0 = x0 / self.scale
            pdf_y0 = y0 / self.scale
            pdf_x1 = x1 / self.scale
            pdf_y1 = y1 / self.scale
            rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            self.page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

        # Apply text annotations
        for x, y, text, _, font_size in self.text_annotations:
            pdf_x = x / self.scale
            pdf_y = y / self.scale
            self.page.insert_text((pdf_x, pdf_y), text, fontsize=font_size)

        # Clear the temporary annotations
        self.erasures.clear()
        self.text_annotations.clear()
        self.clear_selection_rects()
        self.render_page()
        self.update_unselect_buttons()

    def save_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path:
            # Apply erasures
            for x0, y0, x1, y1 in self.erasures:
                # Convert screen coordinates back to PDF coordinates
                pdf_x0 = x0 / self.scale
                pdf_y0 = y0 / self.scale
                pdf_x1 = x1 / self.scale
                pdf_y1 = y1 / self.scale
                rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                self.page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

            # Apply text annotations
            for x, y, text, _, font_size in self.text_annotations:
                # Convert screen coordinates back to PDF coordinates
                pdf_x = x / self.scale
                pdf_y = y / self.scale
                self.page.insert_text((pdf_x, pdf_y), text, fontsize=font_size)

            self.doc.save(path)

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

        # Draw text annotations
        for x, y, text, _, font_size in self.text_annotations:
            text_id = self.canvas.create_text(x, y, text=text, fill="black", anchor="nw", 
                                            font=("Arial", font_size))
            # Update the text_id in the annotations list
            self.text_annotations[self.text_annotations.index((x, y, text, _, font_size))] = (x, y, text, text_id, font_size)

        # Update scroll region to match the image size
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
        # Reset scroll position to top-left
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def clear_selection_rects(self):
        for r in self.selection_rects:
            self.canvas.delete(r)
        self.selection_rects.clear()

    def prev_page(self):
        if self.doc and self.page_index > 0:
            # Apply current changes before moving
            if self.erasures or self.text_annotations:
                self.apply_erasure()
            
            self.page_index -= 1
            self.page = self.doc[self.page_index]
            self.erasures.clear()
            self.text_annotations.clear()
            self.clear_selection_rects()
            self.render_page()
            self.update_nav_buttons()
            self.update_unselect_buttons()

    def next_page(self):
        if self.doc and self.page_index < self.doc.page_count - 1:
            # Apply current changes before moving
            if self.erasures or self.text_annotations:
                self.apply_erasure()
            
            self.page_index += 1
            self.page = self.doc[self.page_index]
            self.erasures.clear()
            self.text_annotations.clear()
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

    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not path:
            return
        self.doc = fitz.open(path)
        self.page_index = 0
        self.page = self.doc[self.page_index]
        self.erasures.clear()
        self.text_annotations.clear()
        self.clear_selection_rects()

        self.apply_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.text_btn.config(state=tk.NORMAL, relief=tk.RAISED)
        self.remove_text_btn.config(state=tk.NORMAL, relief=tk.RAISED)
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.doc.page_count > 1 else tk.DISABLED)
        self.update_unselect_buttons()

        # Reset modes and scale
        self.text_mode = False
        self.remove_text_mode = False
        self.font_size_combo.config(state="disabled")
        self.scale = 2.0  # Reset to default scale

        self.render_page()

    def zoom_in(self):
        if self.scale + self.scale_step <= self.max_scale:
            old_scale = self.scale
            self.scale += self.scale_step
            self._scale_coordinates(old_scale)
            self.render_page()

    def zoom_out(self):
        if self.scale - self.scale_step >= self.min_scale:
            old_scale = self.scale
            self.scale -= self.scale_step
            self._scale_coordinates(old_scale)
            self.render_page()

    def _scale_coordinates(self, old_scale):
        # Scale text annotations
        scaled_annotations = []
        for x, y, text, _, font_size in self.text_annotations:
            # Scale coordinates based on the ratio of new scale to old scale
            new_x = x * (self.scale / old_scale)
            new_y = y * (self.scale / old_scale)
            scaled_annotations.append((new_x, new_y, text, None, font_size))
        self.text_annotations = scaled_annotations

        # Scale erasures
        scaled_erasures = []
        for x0, y0, x1, y1 in self.erasures:
            # Scale coordinates based on the ratio of new scale to old scale
            new_x0 = x0 * (self.scale / old_scale)
            new_y0 = y0 * (self.scale / old_scale)
            new_x1 = x1 * (self.scale / old_scale)
            new_y1 = y1 * (self.scale / old_scale)
            scaled_erasures.append((new_x0, new_y0, new_x1, new_y1))
        self.erasures = scaled_erasures

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
        self.text_annotations.clear()
        self.clear_selection_rects()
        self.update_unselect_buttons()

    def on_right_start(self, event):
        if self.text_mode:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Check if clicked on existing text
            for i, (tx, ty, text, _, font_size) in enumerate(self.text_annotations):
                # Create a temporary text item to get its bbox
                temp_text = self.canvas.create_text(tx, ty, text=text, anchor="nw", font=("Arial", font_size))
                bbox = self.canvas.bbox(temp_text)
                self.canvas.delete(temp_text)
                
                if bbox and x >= bbox[0] and x <= bbox[2] and y >= bbox[1] and y <= bbox[3]:
                    # Start dragging the text
                    self.dragging_text = True
                    self.selected_text_index = i
                    self.drag_start_x = x - tx
                    self.drag_start_y = y - ty
                    self.canvas.config(cursor="fleur")  # Change cursor to indicate dragging
                    return

    def on_right_drag(self, event):
        if self.text_mode and self.dragging_text and self.selected_text_index >= 0:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Calculate new position
            new_x = x - self.drag_start_x
            new_y = y - self.drag_start_y
            
            # Update the text position in the annotations list
            x, y, text, _, font_size = self.text_annotations[self.selected_text_index]
            self.text_annotations[self.selected_text_index] = (new_x, new_y, text, _, font_size)
            
            # Redraw the page to show the new position
            self.render_page()

    def on_right_release(self, event):
        if self.text_mode and self.dragging_text:
            self.dragging_text = False
            self.selected_text_index = -1
            self.canvas.config(cursor="crosshair")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFEditorApp(root)
    root.mainloop()
