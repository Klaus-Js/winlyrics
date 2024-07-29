import cv2
import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import distance

def rgb_to_hex(color):
    return "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])

def get_contrasting_colors(image, num_colors=5):
    def get_dominant_colors(image, num_colors=5):
        # Load image
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Reshape image to be a list of pixels
        pixels = image_rgb.reshape(-1, 3)

        # Fit KMeans clustering
        kmeans = KMeans(n_clusters=num_colors)
        kmeans.fit(pixels)

        # Get the dominant colors
        colors = kmeans.cluster_centers_.astype(int)
        counts = np.bincount(kmeans.labels_)
        return colors, counts

    def convert_to_hsv(colors):
        # Convert RGB colors to HSV
        colors_rgb = np.array(colors, dtype=np.uint8)
        colors_rgb = colors_rgb.reshape(-1, 1, 3)  # Reshape to 1x1x3 for conversion
        colors_hsv = cv2.cvtColor(colors_rgb, cv2.COLOR_RGB2HSV)
        return colors_hsv.reshape(-1, 3)

    def find_most_saturated_color(colors):
        colors_hsv = convert_to_hsv(colors)
        saturations = colors_hsv[:, 1]  # Saturation is the second channel in HSV
        return colors[np.argmax(saturations)]

    def find_highest_contrast_color(base_color, colors):
        max_distance = 0
        contrast_color = None

        # Calculate the Euclidean distance between the base color and each other color
        for color in colors:
            dist = distance.euclidean(base_color, color)
            if dist > max_distance:
                max_distance = dist
                contrast_color = color

        return contrast_color

    # Load image and find dominant colors
    colors, counts = get_dominant_colors(image, num_colors)

    # Find the most saturated color
    most_saturated_color = find_most_saturated_color(colors)

    # Find the color that contrasts the most with the most saturated color
    most_dominant_index = np.argmax(counts)
    remaining_colors = np.delete(colors, most_dominant_index, axis=0)
    contrast_color = find_highest_contrast_color(most_saturated_color, remaining_colors)

    # Convert colors to hex strings
    most_saturated_color_hex = rgb_to_hex(most_saturated_color)
    contrast_color_hex = rgb_to_hex(contrast_color)

    return (most_saturated_color_hex, contrast_color_hex)

