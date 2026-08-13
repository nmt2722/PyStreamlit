import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="RC Section Analysis", layout="wide")

# ==========================================
# 1. IS 456 Material Models & Core Engine
# ==========================================

def get_fc(strain, fck):
    """IS 456 Parabolic-Rectangular Concrete Stress Block"""
    if strain <= 0:
        return 0.0  # Tension ignored
    elif strain < 0.002:
        return 0.45 * fck * (2 * (strain / 0.002) - (strain / 0.002)**2)
    elif strain <= 0.0035:
        return 0.45 * fck
    else:
        return 0.0 # Beyond crushing

def get_fs(strain, fy):
    """Simplified Elastoplastic Steel Model"""
    Es = 200000.0 # MPa
    yield_strain = 0.87 * fy / Es + 0.002
    
    if abs(strain) > yield_strain:
        return np.sign(strain) * 0.87 * fy
    else:
        return np.sign(strain) * (abs(strain) * Es)

def compute_pm_curve(D, geometry_func, steel_bars, fck, fy):
    """Numerical integration to generate the P-M Interaction Curve"""
    P_vals, M_vals = [], []
    
    # Define a sequence of strain profiles (eps_top, eps_bottom) to trace the envelope
    profiles = []
    # 1. Pure Compression
    profiles.append((0.002, 0.002))
    # 2. Compression + Bending (Pivot at top crushing strain)
    for eps_bot in np.linspace(0.002, -0.015, 60):
        profiles.append((0.0035, eps_bot))
    # 3. Pure Tension
    profiles.append((-0.01, -0.01))

    N_steps = 100 # Slices for numerical integration
    dy = D / N_steps

    for eps_top, eps_bot in profiles:
        P, M = 0.0, 0.0
        
        # Concrete Integration
        for i in range(N_steps):
            y = (i + 0.5) * dy
            b = geometry_func(y)
            dA = b * dy
            eps = eps_top - (y / D) * (eps_top - eps_bot)
            fc = get_fc(eps, fck)
            
            P += fc * dA
            M += fc * dA * (D / 2 - y) # Moment about centroid
            
        # Steel Integration
        for y_i, A_si in steel_bars:
            eps_s = eps_top - (y_i / D) * (eps_top - eps_bot)
            fs = get_fs(eps_s, fy)
            
            # Deduct concrete force displaced by steel if in compression
            fc_disp = get_fc(eps_s, fck) if eps_s > 0 else 0
            
            P += (fs - fc_disp) * A_si
            M += (fs - fc_disp) * A_si * (D / 2 - y_i)
            
        # Convert to kN and kNm
        P_vals.append(P / 1000)
        M_vals.append(abs(M / 1000000))

    return P_vals, M_vals

# ==========================================
# 2. Sidebar Navigation
# ==========================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to Page:", ["1. Rectangular P-M", "2. Circular P-M", "3. Strain Visualizer"])

# ==========================================
# PAGE 1: Rectangular Sections
# ==========================================
if page == "1. Rectangular P-M":
    st.title("Rectangular Section P-M Interaction Curve")
    st.write("Generates the Capacity curve extending down into the tension zone.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Section Properties")
        b = st.number_input("Width (b) [mm]", value=300)
        D = st.number_input("Depth (D) [mm]", value=450)
        fck = st.number_input("Concrete Grade (fck) [MPa]", value=25)
        fy = st.number_input("Steel Grade (fy) [MPa]", value=500)
        cover = st.number_input("Effective Cover [mm]", value=40)
        ast = st.number_input("Total Steel Area [mm²]", value=1600)
        
    with col2:
        # Define geometry and steel (Assume half steel top, half bottom)
        geom_func = lambda y: b
        steel_bars = [(cover, ast/2), (D - cover, ast/2)]
        
        P_curve, M_curve = compute_pm_curve(D, geom_func, steel_bars, fck, fy)
        
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(M_curve, P_curve, color='blue', linewidth=2, label='Capacity Envelope')
        ax.axhline(0, color='black', linewidth=1)
        ax.axvline(0, color='black', linewidth=1)
        
        # Mark Tension Capacity
        min_P = min(P_curve)
        ax.plot(0, min_P, 'ro', label=f'Pure Tension Capacity: {min_P:.1f} kN')
        
        ax.set_title(f"P-M Curve: {b}x{D} mm, fck={fck}, fy={fy}")
        ax.set_xlabel("Bending Moment (kNm)")
        ax.set_ylabel("Axial Force (kN) [+ve Comp, -ve Tension]")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()
        st.pyplot(fig)

# ==========================================
# PAGE 2: Circular Sections
# ==========================================
elif page == "2. Circular P-M":
    st.title("Circular Section P-M Interaction Curve")
    st.write("Solves for the exact tension capacity using numerical integration of circular strips.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Section Properties")
        dia = st.number_input("Diameter (D) [mm]", value=500)
        fck = st.number_input("Concrete Grade (fck) [MPa]", value=30)
        fy = st.number_input("Steel Grade (fy) [MPa]", value=500)
        cover = st.number_input("Effective Cover [mm]", value=50)
        num_bars = st.number_input("Number of Bars", value=8, step=1, min_value=4)
        bar_dia = st.number_input("Bar Diameter [mm]", value=20)
        
    with col2:
        R = dia / 2
        A_bar = (np.pi / 4) * (bar_dia ** 2)
        r_s = R - cover # Radius of reinforcement ring
        
        # Circular Geometry width function
        geom_func = lambda y: 2 * np.sqrt(max(0, R**2 - (R - y)**2))
        
        # Calculate bar positions
        angles = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
        steel_bars = []
        for angle in angles:
            y_pos = R - r_s * np.cos(angle) # Depth from top
            steel_bars.append((y_pos, A_bar))
            
        P_curve, M_curve = compute_pm_curve(dia, geom_func, steel_bars, fck, fy)
        
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(M_curve, P_curve, color='green', linewidth=2, label='Capacity Envelope')
        ax.axhline(0, color='black', linewidth=1)
        ax.axvline(0, color='black', linewidth=1)
        
        # Highlight Tension Capacity (Bottom of curve)
        min_P = min(P_curve)
        ax.plot(0, min_P, 'ro', label=f'Pure Tension Capacity: {min_P:.1f} kN')
        
        ax.set_title(f"P-M Curve: Ø{dia} mm, {num_bars}-Ø{bar_dia} bars")
        ax.set_xlabel("Bending Moment (kNm)")
        ax.set_ylabel("Axial Force (kN) [+ve Comp, -ve Tension]")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend()
        st.pyplot(fig)

# ==========================================
# PAGE 3: Interactive Strain Visualizer
# ==========================================
elif page == "3. Strain Visualizer":
    st.title("Circular Section Strain Visualizer")
    st.write("Understand how the Neutral Axis divides the section into Tension and Compression.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Controls")
        xu_ratio = st.slider("Neutral Axis Depth (x_u / D)", min_value=-0.5, max_value=1.5, value=0.6, step=0.05)
        num_bars = st.slider("Number of Reinforcement Bars", min_value=4, max_value=16, value=8, step=2)
        
    with col2:
        D = 1.0  
        R = D / 2  
        cover = 0.15  
        rs = R - cover  
        
        fig, ax = plt.subplots(figsize=(5, 5))
        
        # 1. Concrete Cross-Section
        concrete = plt.Circle((0, 0), R, color='lightgrey', alpha=0.5)
        ax.add_patch(concrete)
        
        # 2. Neutral Axis
        y_na = R - (xu_ratio * D)
        ax.axhline(y_na, color='red', linestyle='--', linewidth=2, label="Neutral Axis")
        
        # Compression Zone Shading
        if y_na < R:
            y_na_clamp = max(y_na, -R) # Prevent math domain errors
            y_shade = np.linspace(y_na_clamp, R, 100)
            x_shade = np.sqrt(R**2 - y_shade**2)
            ax.fill_betweenx(y_shade, -x_shade, x_shade, color='lightblue', alpha=0.6, label="Compression Zone")
            
        # 3. Reinforcement Bars
        angles = np.linspace(0, 2 * np.pi, num_bars, endpoint=False)
        for angle in angles:
            bar_x = rs * np.cos(angle)
            bar_y = rs * np.sin(angle)
            
            bar_color = 'blue' if bar_y > y_na else 'orange'
            bar = plt.Circle((bar_x, bar_y), 0.03, color=bar_color)
            ax.add_patch(bar)
            
        # Format
        ax.set_aspect('equal')
        ax.set_xlim(-R * 1.2, R * 1.2)
        ax.set_ylim(-R * 1.2, R * 1.2)
        # Dummy plots for legend
        ax.plot([], [], 'o', color='blue', label='Bars in Comp.')
        ax.plot([], [], 'o', color='orange', label='Bars in Tension')
        ax.legend(loc="upper right", bbox_to_anchor=(1.5, 1))
        plt.axis('off')
        
        st.pyplot(fig)