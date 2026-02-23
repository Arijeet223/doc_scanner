import sys
import json
import os
import cv2

def setup_template(image_path="input.png"):
    if not os.path.exists(image_path):
        print(f"Error: Could not find '{image_path}'. Please save your screenshot as '{image_path}' in this folder.")
        sys.exit(1)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read '{image_path}'. It might not be a valid image format.")
        sys.exit(1)
        
    # --- Image scaling for display ---
    # Get original dimensions
    orig_h, orig_w = img.shape[:2]
    
    # Target maximum dimensions (fits on most 1080p screens)
    max_display_h = 800
    max_display_w = 1400
    
    # Calculate scale factor
    scale_w = max_display_w / orig_w if orig_w > max_display_w else 1.0
    scale_h = max_display_h / orig_h if orig_h > max_display_h else 1.0
    scale = min(scale_w, scale_h)
    
    # Resize image for display if necessary
    display_img = img
    if scale < 1.0:
        display_img = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)))
    
    # Inverse scale to map coordinates back to original image
    inv_scale = 1.0 / scale
    
    print("=== Bounding Box Setup ===")
    print("A window will open for each field.")
    print("1. Click and drag to draw a box around the exact text you want to extract.")
    print("2. Press SPACE or ENTER to confirm the selection.")
    print("   If you mess up, press 'c' to cancel and redraw.")
    print("==========================")
    
    fields = [
        "case_number", 
        "claimed_amount", 
        "approved_amount", 
        "scheme", 
        "action_taken", 
        "remarks"
    ]
    template = {}
    
    for field in fields:
        print(f"\nPlease select the region for: '{field}'")
        
        # Select ROI on the (potentially resized) display image
        roi = cv2.selectROI(f"Select {field}", display_img, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(f"Select {field}")
        
        x_display, y_display, w_display, h_display = roi
        
        # Map back to original image coordinates
        x = int(x_display * inv_scale)
        y = int(y_display * inv_scale)
        w = int(w_display * inv_scale)
        h = int(h_display * inv_scale)
        
        template[field] = {
            "x1": x,
            "y1": y,
            "x2": x + w,
            "y2": y + h
        }
        print(f"Saved {field} -> x1: {x}, y1: {y}, x2: {x+w}, y2: {y+h}")
        
    with open("template.json", "w") as f:
        json.dump(template, f, indent=4)
        
    print("\n✔ template.json successfully updated! You can now run main.py")

if __name__ == "__main__":
    setup_template()
