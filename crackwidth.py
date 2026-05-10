import streamlit as st
import math
from scipy import optimize

# ==========================================
# 1. ENGINEERING CALCULATION ENGINE
# ==========================================

def solve_rectangular_na(b, d, Ast, m):
    """ Solves neutral axis for rectangular sections using quadratic formula. """
    A = b / 2.0
    B = m * Ast
    C = -m * Ast * d
    x = (-B + math.sqrt(B**2 - 4*A*C)) / (2*A)
    return x

def solve_circular_na_scipy(D, cover, dia, num_bars, Ast, m):
    """ Numerically solves the neutral axis for a circular section using SciPy. """
    R = D / 2.0
    rs = R - cover - (dia / 2.0)
    A_bar = Ast / num_bars
    
    bar_angles = [i * (2 * math.pi / num_bars) for i in range(num_bars)]
    bar_depths = [R + rs * math.cos(angle) for angle in bar_angles] 
    
    def moment_balance(x):
        if x <= 0: return -1.0 
        if x >= D: return 1.0
        
        ratio = max(-1.0, min(1.0, 1 - (x / R))) 
        theta_c = 2 * math.acos(ratio)
        Ac = (R**2 / 2.0) * (theta_c - math.sin(theta_c))
        
        if theta_c == 0:
            y_c = R
        else:
            y_c = (4 * R * math.sin(theta_c / 2)**3) / (3 * (theta_c - math.sin(theta_c)))
        
        dist_c = x - (R - y_c)
        Mc = Ac * dist_c
        
        Ms = sum((m * A_bar) * (d_i - x) for d_i in bar_depths if d_i > x)
        return Mc - Ms

    try:
        x_na = optimize.bisect(moment_balance, 0.001, D - 0.001)
    except ValueError:
        raise ValueError("Could not find a valid Neutral Axis. Check input parameters.")
            
    return x_na, bar_depths

def calculate_crack_width(section_type, params):
    Es = 200000.0  
    Ec = 5000.0 * math.sqrt(params['fck'])
    m = Es / Ec
    
    cover = params['cover']
    dia = params['dia']
    Ast = params['Ast']
    M = params['M']
    
    if section_type in ["Rectangular Beam", "Slab (1m strip)"]:
        b = 1000.0 if section_type == "Slab (1m strip)" else params['b']
        h = params['h']
        spacing = params.get('spacing', 150.0)
        d = h - cover - (dia / 2.0)
        
        x = solve_rectangular_na(b, d, Ast, m)
        z = d - (x / 3.0)
        fs = (M * 1e6) / (Ast * z)
        eps_1 = (fs / Es) * ((h - x) / (d - x))
        
        a = h
        stiffening = (b * (h - x) * (a - x)) / (3 * Es * Ast * (d - x))
        eps_m = eps_1 - stiffening
        
        a_cr = math.sqrt((cover + dia/2)**2 + (spacing/2)**2) - (dia/2)
        
    elif section_type == "Circular Section":
        h = params['D']  
        num_bars = params['num_bars']
        D = params['D']
        
        x, bar_depths = solve_circular_na_scipy(D, cover, dia, num_bars, Ast, m)
        
        tension_depths = [d_i for d_i in bar_depths if d_i > x]
        if not tension_depths:
            raise ValueError("Neutral axis is outside the section or no bars in tension.")
        d = sum(tension_depths) / len(tension_depths)
        
        z = d - (x / 3.0) 
        fs = (M * 1e6) / (Ast * z)
        eps_1 = (fs / Es) * ((h - x) / (d - x))
        
        bt = D 
        stiffening = (bt * (h - x) * (h - x)) / (3 * Es * Ast * (d - x))
        eps_m = eps_1 - stiffening
        
        R = D / 2.0
        rs = R - cover - (dia/2)
        theta = (2 * math.pi) / num_bars
        chord = 2 * rs * math.sin(theta / 2)
        a_cr = math.sqrt((cover + dia/2)**2 + (chord/2)**2) - (dia/2)

    if eps_m <= 0:
        return 0.0, x, fs, eps_m, a_cr, d
        
    numerator = 3 * a_cr * eps_m
    denominator = 1 + 2 * ((a_cr - cover) / (h - x))
    W_cr = numerator / denominator
    
    return W_cr, x, fs, eps_m, a_cr, d

# ==========================================
# 2. STREAMLIT APP & PAGE ROUTING
# ==========================================

st.set_page_config(page_title="IS 456 Crack Width App", layout="wide", page_icon="🏗️")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["🧮 Calculator", "🧠 Theory & Implementation"])

st.sidebar.divider()
st.sidebar.info("**Standard limit per IS 456:**\n\nGenerally **0.3 mm**.\n\nFor aggressive environments, **0.2 mm** or **0.1 mm** may apply.")

# ==========================================
# PAGE 1: CALCULATOR
# ==========================================
if page == "🧮 Calculator":
    st.markdown("""
        <div style='background-color:#0f172a; padding:20px; border-radius:10px; margin-bottom:20px'>
        <h1 style='color:white; margin:0;'>IS 456 Crack Width Calculator</h1>
        <p style='color:#94a3b8; margin:0;'>Analyze concrete flexural sections for Serviceability Limit State (SLS).</p>
        </div>
        """, unsafe_allow_html=True)

    col_input, col_output = st.columns([1, 1.5], gap="large")
    
    with col_input:
        st.subheader("1. Define Section")
        section_type = st.selectbox("Section Geometry", ["Rectangular Beam", "Slab (1m strip)", "Circular Section"])
        
        params = {}
        col_a, col_b = st.columns(2)
        params['fck'] = col_a.number_input("Concrete Grade (fck) [MPa]", value=30.0, step=5.0)
        params['M'] = col_b.number_input("Service Moment [kN-m]", value=80.0, step=5.0)
        
        st.subheader("2. Reinforcement")
        col_c, col_d = st.columns(2)
        params['cover'] = col_c.number_input("Clear Cover [mm]", value=40.0, step=5.0)
        params['dia'] = col_d.number_input("Bar Dia (φ) [mm]", value=20.0, step=2.0)
        
        if section_type == "Circular Section":
            params['D'] = st.number_input("Overall Diameter (D) [mm]", value=600.0, step=50.0)
            params['num_bars'] = st.number_input("Number of Bars", value=8, step=1, min_value=4)
            A_bar = (math.pi / 4.0) * (params['dia']**2)
            params['Ast'] = A_bar * params['num_bars']
            st.caption(f"Calculated Ast: **{params['Ast']:.2f} mm²**")
        else:
            if section_type == "Rectangular Beam":
                params['b'] = st.number_input("Width (b) [mm]", value=300.0, step=10.0)
            params['h'] = st.number_input("Overall Depth (h) [mm]", value=500.0, step=10.0)
            
            col_e, col_f = st.columns(2)
            params['Ast'] = col_e.number_input("Ast [mm²]", value=1256.0, step=10.0)
            params['spacing'] = col_f.number_input("Bar Spacing [mm]", value=150.0, step=10.0)

        calc_btn = st.button("Compute Crack Width", type="primary", use_container_width=True)

    with col_output:
        if calc_btn:
            try:
                W_cr, x, fs, eps_m, a_cr, d = calculate_crack_width(section_type, params)
                
                st.subheader("Diagnostic Results")
                st.markdown("Use these intermediate values to verify the software against hand calculations.")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Neutral Axis (x)", f"{x:.1f} mm")
                m2.metric("Effective Depth (d)", f"{d:.1f} mm")
                m3.metric("Steel Stress (fs)", f"{fs:.1f} MPa")
                
                m4, m5, m6 = st.columns(3)
                m4.metric("Avg Strain (εm)", f"{eps_m:.6f}")
                m5.metric("Critical Dist (a_cr)", f"{a_cr:.1f} mm")
                m6.metric("Design Crack Width", f"{W_cr:.3f} mm")
                
                st.divider()
                
                if W_cr <= 0:
                    st.success("✅ **Section is Uncracked.** The moment is too low to induce tension cracking.")
                elif W_cr <= 0.3:
                    st.success(f"✅ **Safe.** Crack Width is **{W_cr:.3f} mm**. (Passes standard 0.3 mm limit).")
                else:
                    st.error(f"⚠️ **Warning.** Crack Width is **{W_cr:.3f} mm**, exceeding general 0.3 mm limits.")
                    
            except Exception as e:
                st.error(f"Calculation Error: {e}")

# ==========================================
# PAGE 2: THEORY & DOCUMENTATION
# ==========================================
elif page == "🧠 Theory & Implementation":
    st.title("Brain-Friendly Theory & Reference")
    st.markdown("Understanding the physics behind IS 456 Annex F.")

    st.header("1. Why Do We Calculate Crack Width?")
    st.markdown("""
    Concrete cracks. It's a fundamental reality of reinforced concrete—we put steel in it specifically *because* we expect the concrete to crack under tension. 
    However, if cracks get too wide, three bad things happen:
    *   **Corrosion:** Water and oxygen reach the rebar, causing it to rust and expand (spalling).
    *   **Aesthetics:** People get scared when they see massive cracks in their ceilings.
    *   **Water-tightness:** Tanks and retaining walls will leak.
    """)

    st.header("2. Decoding the IS 456 Formula")
    st.info("The IS 456 formula looks intimidating, but it is just geometry and material science combined.")
    st.latex(r"W_{cr} = \frac{3 a_{cr} \epsilon_m}{1 + 2 \left( \frac{a_{cr} - c_{min}}{h - x} \right)}")
    
    # Note the 'r' prefix added here to make it a raw string
    st.markdown(r"""
    Let's break down the cast of characters:
    *   **$W_{cr}$ (The Output):** The width of the crack at the surface of the concrete.
    *   **$a_{cr}$ (The Geometry):** The distance from where you are standing to the surface of the nearest steel bar. Cracks are always widest halfway between two bars.
    *   **$\epsilon_m$ (The Stretch):** The average strain. Think of this as how much the concrete surface is physically stretching at that specific level.
    """)

    st.header("3. The Concept of 'Tension Stiffening'")
    # Note the 'r' prefix added here
    st.markdown(r"""
    When you pull on a bare steel bar, it stretches uniformly. But when that steel bar is buried inside concrete, the concrete *clings* to the steel between the cracks.
    
    This clinging action restricts the steel from stretching fully. The concrete is "stiffening" the tension zone. This is why we don't just calculate the strain of bare steel ($\epsilon_1$), we calculate the **average strain** ($\epsilon_m$) by subtracting the stiffening effect:
    
    $$ \epsilon_m = \epsilon_1 - \text{Stiffening Effect} $$
    
    If you have a massive concrete beam with very little steel, the stiffening effect is huge. 
    """)

    st.header("4. Program Implementation & Python Logic")
    st.markdown("""
    *   **Rectangular Beams/Slabs:** The program uses standard elastic cracked-section theory. We find the neutral axis by solving a simple quadratic equation representing the balance of first moments of area.
    *   **Circular Sections (The Hard Part):** Circular columns are difficult because as the neutral axis moves up or down, the width of the concrete slice changes non-linearly. We cannot use a simple formula.
        *   **The SciPy Solution:** This program utilizes `scipy.optimize.bisect`. It makes an initial guess for the neutral axis, calculates the compression moment and tension moment, and mathematically zeroes in on the exact balance point in milliseconds.
    """)

    st.header("5. Professional Disclaimers")
    # Note the 'r' prefix added here
    st.warning(r"""
    **Software Liability & Engineering Judgment**
    *   **No Black Boxes:** This tool outputs all intermediate variables ($x$, $d$, $f_s$, $\epsilon_m$). As a professional, you should spot-check these against manual calculations.
    *   **Pure Flexure Assumption:** This tool assumes the section is subjected to pure bending moments. It does not account for axial compression (which generally reduces crack widths) or axial tension (which exacerbates them).
    *   **Liability:** This software is provided "as is". The structural engineer of record is fully responsible for all final design decisions and safety verifications.
    """)