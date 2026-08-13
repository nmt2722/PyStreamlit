import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

# Set up the web page title
st.title("Circular Section Strain Visualizer")
st.write("Adjust the Neutral Axis to see the tension and compression zones.")

# Create interactive sliders in the sidebar
xu_ratio = st.sidebar.slider("Neutral Axis Depth (x_u / D)", min_value=-0.5, max_value=1.5, value=0.5, step=0.05)
num_bars = st.sidebar.slider("Number of Reinforcement Bars", min_value=4, max_value=16, value=8, step=2)

# Geometry definitions
D = 1.0  # Diameter
R = D / 2  # Radius
cover = 0.1  # Effective cover ratio
rs = R - cover  # Radius of the reinforcement ring

# Create the plot
fig, ax = plt.subplots(figsize=(6, 6))

# 1. Draw the Concrete Cross-Section
concrete_circle = plt.Circle((0, 0), R, color='lightgrey', alpha=0.5, label="Concrete")
ax.add_patch(concrete_circle)

# 2. Draw the Neutral Axis
# Y-coordinate of the NA (Assuming top of circle is Y = R)
y_na = R - (xu_ratio * D)
ax.axhline(y_na, color='red', linestyle='--', linewidth=2, label="Neutral Axis")

# Shade the compression zone (Above NA)
if y_na < R:
    y_shade = np.linspace(y_na, R, 100)
    x_shade = np.sqrt(R**2 - y_shade**2)
    ax.fill_betweenx(y_shade, -x_shade, x_shade, color='lightblue', alpha=0.5, label="Compression Zone")

# 3. Draw the Reinforcement Bars
angles = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
for angle in angles:
    # Calculate bar coordinates
    bar_x = rs * np.cos(angle)
    bar_y = rs * np.sin(angle)
    
    # Determine if bar is in tension or compression
    if bar_y > y_na:
        bar_color = 'blue' # Compression
    else:
        bar_color = 'orange' # Tension
        
    bar = plt.Circle((bar_x, bar_y), 0.03, color=bar_color)
    ax.add_patch(bar)

# Plot formatting
ax.set_aspect('equal')
ax.set_xlim(-R * 1.2, R * 1.2)
ax.set_ylim(-R * 1.2, R * 1.2)
ax.set_title(f"Neutral Axis at {xu_ratio:.2f}D")
ax.legend(loc="upper right", bbox_to_anchor=(1.4, 1))
plt.axis('off')

# Render the plot in Streamlit
st.pyplot(fig)