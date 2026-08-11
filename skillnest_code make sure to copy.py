import io
import os
import random
import smtplib
import time
import json
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
import mathgenerator as mg

# ============================================================
# MISTRAL API KEY
# Put your NEW Mistral API key between the quotes below.
# Do NOT share the key publicly.
# ============================================================
MISTRAL_API_KEY = "jCUAi0GOkbYkSc8o8hJlv6bGD1eLrbxs"

# Page Configuration
st.set_page_config(
    page_title="Skill Nest - AP Syllabus Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Upgraded Fast Clean Themes Styling
st.markdown("""
    <style>
    .stButton>button {
        background: linear-gradient(135deg, #2b6cb0 0%, #1a365d 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.2s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #2c5282 0%, #2b6cb0 100%);
        box-shadow: 0 4px 12px rgba(43, 108, 176, 0.3);
    }
    .header-card {
        background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .meet-card {
        background: #f0fff4;
        border-left: 5px solid #38a169;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)


# Global Persistent Store (Simulating 1-Month Persistence)
@st.cache_resource
def get_global_database():
    return {
        "registered_students": {},
        "active_slots": [],
        "quiz_results": [],
        "active_memory_notes": []
    }


db = get_global_database()

# Session State Initialization
if "current_page" not in st.session_state: st.session_state.current_page = "login"
if "user" not in st.session_state: st.session_state.user = ""
if "email" not in st.session_state: st.session_state.email = ""
if "phone" not in st.session_state: st.session_state.phone = ""
if "student_id" not in st.session_state: st.session_state.student_id = ""
if "otp_code" not in st.session_state: st.session_state.otp_code = ""
if "plan" not in st.session_state: st.session_state.plan = None
if "ai_answer" not in st.session_state: st.session_state.ai_answer = ""
if "ai_question" not in st.session_state: st.session_state.ai_question = ""
if "ai_reading_complete" not in st.session_state: st.session_state.ai_reading_complete = False
if "active_memory_started_at" not in st.session_state: st.session_state.active_memory_started_at = None
if "active_memory_notes" not in st.session_state: st.session_state.active_memory_notes = ""
if "grade" not in st.session_state: st.session_state.grade = "Grade 5"
if "board" not in st.session_state: st.session_state.board = "AP State Board"
if "meet_link" not in st.session_state: st.session_state.meet_link = "https://meet.google.com/abc-defg-hij"
if "teacher_email" not in st.session_state: st.session_state.teacher_email = "mahith.balegar@gmail.com"


# Helper function to send HTML emails
def send_html_email(to_email, subject, html_content):
    try:
        sender = "mahith.balegar@gmail.com"
        password = "vwqq hkjq kkkq zrjs"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [to_email], msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Email notification failed: {type(e).__name__}: {e}")
        return False


# ============================================================
# ACTIVE MEMORY - AI NOTES -> TEACHER REVIEW
# ============================================================
def submit_active_memory_notes(notes_text, automatic=False):
    notes_text = (notes_text or "").strip()
    if not notes_text:
        notes_text = "No notes entered by the student."

    entry = {
        "id": f"AM-{int(time.time() * 1000)}",
        "student_id": st.session_state.student_id,
        "name": st.session_state.user,
        "email": st.session_state.email,
        "grade": st.session_state.grade,
        "question": st.session_state.ai_question,
        "ai_answer": st.session_state.ai_answer,
        "notes": notes_text,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "automatic": automatic,
        "status": "Pending Teacher Review",
        "teacher_feedback": ""
    }
    db.setdefault("active_memory_notes", []).append(entry)

    auto_label = "automatically after 20 seconds" if automatic else "by the student"
    email_html = f"""
    <html><body style=\"font-family:Arial,sans-serif;\">
    <h2>🧠 Skill Nest Active Memory Submission</h2>
    <p>A student submitted Active Memory notes {auto_label}.</p>
    <ul>
      <li><b>Student:</b> {st.session_state.user}</li>
      <li><b>Student ID:</b> {st.session_state.student_id}</li>
      <li><b>Grade:</b> {st.session_state.grade}</li>
      <li><b>Question:</b> {st.session_state.ai_question}</li>
    </ul>
    <h3>Student Notes</h3>
    <p style=\"white-space:pre-wrap;\">{notes_text}</p>
    <h3>AI Answer</h3>
    <p style=\"white-space:pre-wrap;\">{st.session_state.ai_answer}</p>
    </body></html>
    """
    send_html_email(st.session_state.teacher_email, "Skill Nest - Active Memory Notes Submitted", email_html)

    st.session_state.ai_reading_complete = False
    st.session_state.active_memory_started_at = None
    st.session_state.active_memory_notes = ""
    st.session_state.ai_answer = ""
    st.session_state.ai_question = ""


# Curriculum Databases (Math, Science, SST, English, Telugu)
MATH_SYLLABUS_DATABASE = {
    "Grade 5": [
        {"ch": "Chapter 1: Numbers & Large Scale Operations",
         "notes": "Extends numerals into lakhs and crores using Indian/International place value systems, multi-digit operations, and real-world word problems."},
        {"ch": "Chapter 2: Multiplication & Division",
         "notes": "Covers multi-digit multiplication algorithms, long division with remainders, and unitary method applications."},
        {"ch": "Chapter 3: Factors and Multiples",
         "notes": "Explores prime/composite numbers, divisibility tests, HCF, and LCM through prime factorization."},
        {"ch": "Chapter 4: Fractions and Decimals",
         "notes": "Teaches proper, improper, mixed fractions, unlike fraction arithmetic, and decimal place values connected to metric units."},
        {"ch": "Chapter 5: Basic Geometry & Shapes",
         "notes": "Introduces points, lines, rays, protractor angle measurements, and triangle/quadrilateral classifications."},
        {"ch": "Chapter 6: Data Handling & Pictographs",
         "notes": "Focuses on tally marks, frequency tables, pictographs, and bar graph interpretations."},
        {"ch": "Chapter 7: Patterns and Symmetry",
         "notes": "Explores number sequences, geometric repeating patterns, lines of symmetry, and reflections."},
        {"ch": "Chapter 8: Measurement & Metric Units",
         "notes": "Conversions between length, mass, and capacity units with word problems."},
        {"ch": "Chapter 9: Perimeter and Area Basics",
         "notes": "Calculating boundary lengths and grid-based surface areas."},
        {"ch": "Chapter 10: Time and Calendar",
         "notes": "Reading clock faces, elapsed time calculations, and calendar date arithmetic."},
        {"ch": "Chapter 11: Money and Financial Arithmetic",
         "notes": "Unit pricing, profit & loss basics, and currency calculations."},
        {"ch": "Chapter 12: Revision & Sample Assessments",
         "notes": "Consolidates all Grade 5 math concepts with mixed practice word problems and test papers."}
    ],
    "Grade 6": [
        {"ch": "Chapter 1: Knowing Our Numbers",
         "notes": "Estimation, large numbers up to crores, Indian/International systems, and Roman numerals."},
        {"ch": "Chapter 2: Whole Numbers",
         "notes": "Whole number properties, closure, commutativity, associativity, and distributivity."},
        {"ch": "Chapter 3: Playing with Numbers",
         "notes": "Factors, multiples, prime factorization, HCF, and LCM concepts in depth."},
        {"ch": "Chapter 4: Basic Geometrical Ideas",
         "notes": "Lines, rays, curves, polygons, angles, triangles, and circles."},
        {"ch": "Chapter 5: Understanding Elementary Shapes",
         "notes": "Measuring line segments, angle classifications, and categorizing triangles/quadrilaterals."},
        {"ch": "Chapter 6: Integers",
         "notes": "Negative numbers, number lines, addition/subtraction of integers, and sign conventions."},
        {"ch": "Chapter 7: Fractions",
         "notes": "Fraction representations, proper/improper/mixed types, and basic operations."},
        {"ch": "Chapter 8: Decimals",
         "notes": "Decimal place values, conversions to fractions, and arithmetic operations."},
        {"ch": "Chapter 9: Data Handling", "notes": "Recording data, tally marks, frequency tables, and bar graphs."},
        {"ch": "Chapter 10: Mensuration",
         "notes": "Perimeter and area of closed rectilinear figures, regular polygons, rectangles, and squares."},
        {"ch": "Chapter 11: Algebra",
         "notes": "Using letters for unknown quantities, algebraic expressions, and solving simple linear equations."},
        {"ch": "Chapter 12: Ratio and Proportion",
         "notes": "Comparing quantities using ratios, equivalent ratios, and the unitary method."}
    ],
    "Grade 7": [
        {"ch": "Chapter 1: Integers",
         "notes": "Multiplication and division rules of signed numbers and integer properties."},
        {"ch": "Chapter 2: Fractions and Decimals",
         "notes": "Multiplication and division of fractions and decimals with word problems."},
        {"ch": "Chapter 3: Data Handling",
         "notes": "Arithmetic mean, median, mode, range, double bar graphs, and probability."},
        {"ch": "Chapter 4: Simple Equations",
         "notes": "Solving linear equations with one variable and transposing terms."},
        {"ch": "Chapter 5: Lines and Angles",
         "notes": "Complementary, supplementary, adjacent, vertically opposite angles, and transversal lines."},
        {"ch": "Chapter 6: The Triangle and its Properties",
         "notes": "Medians, altitudes, exterior angle property, and Pythagoras property."},
        {"ch": "Chapter 7: Comparing Quantities",
         "notes": "Ratios, percentages, profit/loss, and simple interest calculations."},
        {"ch": "Chapter 8: Rational Numbers",
         "notes": "Rational numbers on number lines and four basic arithmetic operations."},
        {"ch": "Chapter 9: Perimeter and Area",
         "notes": "Parallelograms, triangles, circles (circumference/area), and composite layouts."},
        {"ch": "Chapter 10: Algebraic Expressions", "notes": "Terms, factors, coefficients, and algebraic identities."},
        {"ch": "Chapter 11: Exponents and Powers",
         "notes": "Laws of exponents and expressing large numbers in standard form."},
        {"ch": "Chapter 12: Symmetry and Visualising Solid Shapes",
         "notes": "Rotational symmetry, 3D shapes, and views of 3D objects."}
    ],
    "Grade 8": [
        {"ch": "Chapter 1: Rational Numbers",
         "notes": "Properties, multiplicative inverse, and distributivity of rational numbers."},
        {"ch": "Chapter 2: Linear Equations in One Variable",
         "notes": "Solving equations with variables on both sides and reducing equations to simpler forms."},
        {"ch": "Chapter 3: Understanding Quadrilaterals",
         "notes": "Polygon classifications, angle sums, and special parallelograms."},
        {"ch": "Chapter 4: Data Handling",
         "notes": "Histograms, pie charts, and experimental/theoretical probabilities."},
        {"ch": "Chapter 5: Squares and Square Roots",
         "notes": "Properties of square numbers, prime factorization, and long division methods."},
        {"ch": "Chapter 6: Cubes and Cube Roots",
         "notes": "Cube numbers, estimation methods, and cube root calculations."},
        {"ch": "Chapter 7: Comparing Quantities",
         "notes": "Compound interest, growth/depreciation formulas, and percentage applications."},
        {"ch": "Chapter 8: Algebraic Expressions and Identities",
         "notes": "Polynomial multiplication and standard algebraic identities."},
        {"ch": "Chapter 9: Mensuration",
         "notes": "Area of trapeziums, surface area, and volume of cylinders, cubes, and cuboids."},
        {"ch": "Chapter 10: Exponents and Powers", "notes": "Negative integer powers and scientific notation."},
        {"ch": "Chapter 11: Direct and Inverse Proportions",
         "notes": "Direct variation, inverse variation, and practical problem-solving."},
        {"ch": "Chapter 12: Factorisation & Introduction to Graphs",
         "notes": "Algebraic factorisation by grouping and Cartesian coordinate graphing."}
    ],
    "Grade 9": [
        {"ch": "Chapter 1: Number Systems",
         "notes": "Irrational numbers, real number decimal expansions, and surd simplifications."},
        {"ch": "Chapter 2: Polynomials",
         "notes": "Polynomials in one variable, zeroes, remainder theorem, and factorisation."},
        {"ch": "Chapter 3: Coordinate Geometry",
         "notes": "Cartesian coordinate systems, axes, quadrants, and plotting points."},
        {"ch": "Chapter 4: Linear Equations in Two Variables",
         "notes": "Solution sets, graphs of linear equations, and geometric representations."},
        {"ch": "Chapter 5: Introduction to Euclid's Geometry",
         "notes": "Axioms, postulates, and equivalent versions of Euclid's fifth postulate."},
        {"ch": "Chapter 6: Lines and Angles",
         "notes": "Interacting lines, parallel lines, angle sum property of triangles."},
        {"ch": "Chapter 7: Triangles", "notes": "Triangle congruence criteria and geometric deductive proofs."},
        {"ch": "Chapter 8: Quadrilaterals", "notes": "Properties of parallelograms and the mid-point theorem."},
        {"ch": "Chapter 9: Circles", "notes": "Chords, arcs, cyclic quadrilaterals, and tangent properties."},
        {"ch": "Chapter 10: Heron's Formula",
         "notes": "Calculating triangle and quadrilateral areas using semi-perimeter."},
        {"ch": "Chapter 11: Surface Areas and Volumes",
         "notes": "Total and curved surface area, and volume for cylinders, cones, and spheres."},
        {"ch": "Chapter 12: Statistics",
         "notes": "Collection of data, frequency polygons, and mean/median/mode for ungrouped data."}
    ],
    "Grade 10": [
        {"ch": "Chapter 1: Real Numbers", "notes": "Euclid's Division Lemma and Fundamental Theorem of Arithmetic."},
        {"ch": "Chapter 2: Polynomials",
         "notes": "Geometrical meaning of zeroes and relationship between coefficients and zeroes."},
        {"ch": "Chapter 3: Pair of Linear Equations in Two Variables",
         "notes": "Graphical and algebraic methods of solution (substitution, elimination)."},
        {"ch": "Chapter 4: Quadratic Equations",
         "notes": "Factorization, completing the square, and quadratic formula."},
        {"ch": "Chapter 5: Arithmetic Progressions",
         "notes": "Common difference, nth term formula, and sum of first n terms."},
        {"ch": "Chapter 6: Triangles",
         "notes": "Similarity of triangles, Thales theorem (BPT), and criteria for similarity."},
        {"ch": "Chapter 7: Coordinate Geometry", "notes": "Distance formula, section formula, and area of a triangle."},
        {"ch": "Chapter 8: Introduction to Trigonometry",
         "notes": "Trigonometric ratios, standard angles, and identities."},
        {"ch": "Chapter 9: Some Applications of Trigonometry",
         "notes": "Heights, distances, angles of elevation and depression."},
        {"ch": "Chapter 10: Circles", "notes": "Tangents to a circle and number of tangents from a point."},
        {"ch": "Chapter 11: Areas Related to Circles", "notes": "Area of sector and segment of a circle."},
        {"ch": "Chapter 12: Statistics and Probability",
         "notes": "Grouped frequency data, mean, median, mode, and empirical probability."}
    ]
}

SCIENCE_SYLLABUS_DATABASE = {
    "Grade 5": [
        {"ch": "Chapter 1: Plant Life & Growth",
         "notes": "Covers seed germination, photosynthesis basics, plant parts, and agricultural crop production cycles."},
        {"ch": "Chapter 2: Animal Habitats & Adaptations",
         "notes": "Explores diverse ecosystems, terrestrial and aquatic adaptations, and food chains."},
        {"ch": "Chapter 3: Food and Health",
         "notes": "Essential nutrients, balanced diet, hygiene, and communicable/non-communicable diseases."},
        {"ch": "Chapter 4: Air, Water and Weather",
         "notes": "Atmospheric layers, water cycle, evaporation, condensation, and weather patterns."},
        {"ch": "Chapter 5: Force, Work and Energy",
         "notes": "Push/pull forces, simple machines, mechanical energy forms, and conservation."},
        {"ch": "Chapter 6: Our Universe & Solar System",
         "notes": "Planets, stars, moon phases, eclipses, and space exploration basics."},
        {"ch": "Chapter 7: Safety and First Aid",
         "notes": "Road safety rules, home hazard prevention, and emergency first aid for cuts/burns."},
        {"ch": "Chapter 8: Rocks and Minerals",
         "notes": "Types of rocks, mineral compositions, gems, and soil formation processes."},
        {"ch": "Chapter 9: Human Body Systems",
         "notes": "Skeletal, muscular, digestive, and nervous system overviews."},
        {"ch": "Chapter 10: Soil Conservation",
         "notes": "Soil layers, erosion factors, afforestation, and farming safeguards."},
        {"ch": "Chapter 11: Natural Disasters",
         "notes": "Earthquakes, floods, droughts, cyclones, and disaster preparedness."},
        {"ch": "Chapter 12: Science Revision & Practice",
         "notes": "Comprehensive review of all Grade 5 scientific concepts and experiments."}
    ],
    "Grade 6": [
        {"ch": "Chapter 1: Food: Where Does It Come From?",
         "notes": "Plant and animal food sources, herbivores, carnivores, omnivores, and balanced diets."},
        {"ch": "Chapter 2: Components of Food",
         "notes": "Nutrients, carbohydrates, proteins, fats, vitamins, minerals, and deficiency diseases."},
        {"ch": "Chapter 3: Fibre to Fabric",
         "notes": "Natural fibers (cotton, jute, silk, wool), synthetic fibers, and spinning/weaving processes."},
        {"ch": "Chapter 4: Sorting Materials into Groups",
         "notes": "Properties of materials, appearance, hardness, solubility, transparency, and flotation."},
        {"ch": "Chapter 5: Separation of Substances",
         "notes": "Methods of separation: handpicking, winnowing, sieving, sedimentation, filtration, and distillation."},
        {"ch": "Chapter 6: Changes Around Us",
         "notes": "Reversible and irreversible physical and chemical changes in everyday life."},
        {"ch": "Chapter 7: Getting to Know Plants",
         "notes": "Herbs, shrubs, trees, stem/leaf structures, root systems, and flower anatomy."},
        {"ch": "Chapter 8: Body Movements",
         "notes": "Human skeletal system, joints, cartilage, muscle contraction, and animal locomotion."},
        {"ch": "Chapter 9: The Living Organisms and Their Surroundings",
         "notes": "Biotic/abiotic factors, habitats, terrestrial/aquatic adaptations, and desert/mountain life."},
        {"ch": "Chapter 10: Motion and Measurement of Distances",
         "notes": "Standard units of measurement, types of motion (rectilinear, circular, periodic)."},
        {"ch": "Chapter 11: Light, Shadows and Reflections",
         "notes": "Luminous/non-luminous objects, transparent/opaque/translucent media, pinhole cameras, and mirrors."},
        {"ch": "Chapter 12: Electricity and Circuits",
         "notes": "Electric cells, bulbs, circuits, conductors, insulators, and switches."}
    ],
    "Grade 7": [
        {"ch": "Chapter 1: Nutrition in Plants",
         "notes": "Autotrophic nutrition, photosynthesis mechanism, and parasitic/insectivorous plants."},
        {"ch": "Chapter 2: Nutrition in Animals",
         "notes": "Ingestion, digestion in humans, rumen digestion in grass-eating animals, and amoeba feeding."},
        {"ch": "Chapter 3: Fibre to Fabric",
         "notes": "Wool processing from sheep/yak/cashmere, silk extraction from silkworms."},
        {"ch": "Chapter 4: Heat",
         "notes": "Temperature measurement, clinical/laboratory thermometers, and heat transfer (conduction, convection, radiation)."},
        {"ch": "Chapter 5: Acids, Bases and Salts",
         "notes": "Natural indicators (litmus, turmeric, china rose), neutralisation reactions in everyday life."},
        {"ch": "Chapter 6: Physical and Chemical Changes",
         "notes": "Physical properties, chemical reactions, rusting of iron, and crystallisation."},
        {"ch": "Chapter 7: Weather, Climate and Adaptations",
         "notes": "Meteorological elements, climate zones, and polar/tropical rainforest adaptations."},
        {"ch": "Chapter 8: Winds, Storms and Cyclones",
         "notes": "Air pressure, wind currents, thunderstorms, and cyclone disaster management."},
        {"ch": "Chapter 9: Soil",
         "notes": "Soil profile, horizons, soil types (sandy, clayey, loamy), percolation rate, and crop suitability."},
        {"ch": "Chapter 10: Respiration in Organisms",
         "notes": "Aerobic and anaerobic cellular respiration, human respiratory tract, and breathing in fish/plants."},
        {"ch": "Chapter 11: Transportation in Animals and Plants",
         "notes": "Human circulatory system, blood vessels, heart, excretion, and xylem/phloem transport in plants."},
        {"ch": "Chapter 12: Reproduction in Plants & Motion/Time",
         "notes": "Asexual and sexual reproduction in plants, seed dispersal, and speed/time graphs."}
    ],
    "Grade 8": [
        {"ch": "Chapter 1: Crop Production and Management",
         "notes": "Agricultural practices, soil preparation, sowing, irrigation methods, and weed protection."},
        {"ch": "Chapter 2: Microorganisms: Friend and Foe",
         "notes": "Bacteria, fungi, protozoa, virus, vaccine development, and food preservation."},
        {"ch": "Chapter 3: Synthetic Fibres and Plastics",
         "notes": "Rayon, nylon, polyester, acrylic, plastic characteristics, and environmental impact."},
        {"ch": "Chapter 4: Materials: Metals and Non-Metals",
         "notes": "Physical and chemical properties of metals and non-metals, displacement reactions."},
        {"ch": "Chapter 5: Coal and Petroleum",
         "notes": "Exhaustible/inexhaustible resources, fossil fuel formation, petroleum refining, and conservation."},
        {"ch": "Chapter 6: Combustion and Flame",
         "notes": "Chemical burning processes, fire control, and candle flame zones."},
        {"ch": "Chapter 7: Conservation of Plants and Animals",
         "notes": "Deforestation causes, biosphere reserves, wildlife sanctuaries, and red data books."},
        {"ch": "Chapter 8: Cell - Structure and Functions",
         "notes": "Discovery of cells, cell organelles, plant vs animal cells, and cell division."},
        {"ch": "Chapter 9: Reproduction in Animals",
         "notes": "Asexual and sexual reproduction, fertilization, viviparous/oviparous animals, and metamorphosis."},
        {"ch": "Chapter 10: Reaching the Age of Adolescence",
         "notes": "Puberty changes, secondary sexual characters, endocrine glands, and reproductive health."},
        {"ch": "Chapter 11: Force and Pressure",
         "notes": "Push/pull forces, contact/non-contact forces, atmospheric pressure, and liquid pressure."},
        {"ch": "Chapter 12: Friction, Sound and Chemical Effects of Electric Current",
         "notes": "Frictional forces, sound wave production, noise pollution, and electroplating."}
    ],
    "Grade 9": [
        {"ch": "Chapter 1: Matter in Our Surroundings",
         "notes": "States of matter, particle nature, diffusion, evaporation, and latent heat."},
        {"ch": "Chapter 2: Is Matter Around Us Pure?",
         "notes": "Pure substances, mixtures, colloids, suspensions, and separation techniques."},
        {"ch": "Chapter 3: Atoms and Molecules",
         "notes": "Laws of chemical combination, atomic mass, molecular mass, and mole concept."},
        {"ch": "Chapter 4: Structure of the Atom",
         "notes": "Thomson, Rutherford, and Bohr atomic models, valency, atomic number, and isotopes."},
        {"ch": "Chapter 5: The Fundamental Unit of Life (Cell)",
         "notes": "Cell organelles, plasma membranes, nucleus, cytoplasm, and cell division."},
        {"ch": "Chapter 6: Tissues",
         "notes": "Plant tissues (meristematic, permanent) and animal tissues (epithelial, connective, muscular, nervous)."},
        {"ch": "Chapter 7: Motion",
         "notes": "Distance, displacement, speed, velocity, equations of motion, and graphical analysis."},
        {"ch": "Chapter 8: Force and Laws of Motion",
         "notes": "Newton's three laws of motion, inertia, momentum, and conservation laws."},
        {"ch": "Chapter 9: Gravitation",
         "notes": "Universal law of gravitation, free fall, acceleration due to gravity, mass, and weight."},
        {"ch": "Chapter 10: Work and Energy",
         "notes": "Work done, kinetic energy, potential energy, power, and law of conservation of energy."},
        {"ch": "Chapter 11: Sound",
         "notes": "Wave production, longitudinal waves, echo, reverberation, and human ear anatomy."},
        {"ch": "Chapter 12: Improvement in Food Resources",
         "notes": "Crop variety improvement, nutrient management, animal husbandry, and fisheries."}
    ],
    "Grade 10": [
        {"ch": "Chapter 1: Chemical Reactions and Equations",
         "notes": "Balancing equations, types of reactions (combination, decomposition, displacement, redox)."},
        {"ch": "Chapter 2: Acids, Bases and Salts",
         "notes": "Chemical properties, pH scale, sodium hydroxide, bleaching powder, baking soda, and plaster of Paris."},
        {"ch": "Chapter 3: Metals and Non-Metals",
         "notes": "Chemical reactivity series, ionic bond formation, metallurgy, and corrosion prevention."},
        {"ch": "Chapter 4: Carbon and its Compounds",
         "notes": "Covalent bonding, allotropes, functional groups, homologous series, soaps, and detergents."},
        {"ch": "Chapter 5: Life Processes",
         "notes": "Autotrophic/heterotrophic nutrition, human respiration, circulation, and excretory systems."},
        {"ch": "Chapter 6: Control and Coordination",
         "notes": "Nervous system, reflex arcs, plant hormones, and human endocrine glands."},
        {"ch": "Chapter 7: How do Organisms Reproduce?",
         "notes": "Asexual reproduction, sexual reproduction in flowering plants, and human reproductive health."},
        {"ch": "Chapter 8: Heredity and Evolution",
         "notes": "Mendel's laws of inheritance, sex determination, and evolutionary evidence."},
        {"ch": "Chapter 9: Light - Reflection and Refraction",
         "notes": "Spherical mirrors, lens formula, refraction index, and optical instruments."},
        {"ch": "Chapter 10: Human Eye and Colourful World",
         "notes": "Defects of vision (myopia, hypermetropia), refraction through prism, and atmospheric scattering."},
        {"ch": "Chapter 11: Electricity",
         "notes": "Electric current, potential difference, Ohm's law, resistance combinations, and Joule's heating law."},
        {"ch": "Chapter 12: Magnetic Effects of Electric Current & Our Environment",
         "notes": "Magnetic field lines, electromagnetism, electric motors, generators, and ecosystems."}
    ]
}

SST_SYLLABUS_DATABASE = {
    "Grade 5": [
        {"ch": "Chapter 1: Our Earth & Globes",
         "notes": "Covers latitudes, longitudes, continents, oceans, and basic map reading skills."},
        {"ch": "Chapter 2: Indian Heritage & Government",
         "notes": "Introduces fundamental rights, civic duties, and national symbols of India."},
        {"ch": "Chapter 3: Major Landforms of the Earth",
         "notes": "Mountains, plateaus, plains, valleys, and how landforms shape human settlements."},
        {"ch": "Chapter 4: Rivers and Water Resources",
         "notes": "Major river basins of India, irrigation dams, and water conservation methods."},
        {"ch": "Chapter 5: Climate and Seasons of India",
         "notes": "Monsoons, summer, winter, retreating monsoons, and weather adaptation."},
        {"ch": "Chapter 6: Agriculture and Crops in India",
         "notes": "Food crops (rice, wheat) vs cash crops (cotton, sugarcane) and farming regions."},
        {"ch": "Chapter 7: Minerals and Industries",
         "notes": "Coal, iron ore, petroleum deposits, and major manufacturing industries in India."},
        {"ch": "Chapter 8: Transport and Communication",
         "notes": "Roadways, railways, airways, waterways, postal systems, and digital connectivity."},
        {"ch": "Chapter 9: Our National Symbols and Constitution",
         "notes": "National flag, anthem, emblem, and core democratic values of the Indian Constitution."},
        {"ch": "Chapter 10: Early Human Civilisations",
         "notes": "Stone age hunters, discovery of fire, invention of the wheel, and early agriculture."},
        {"ch": "Chapter 11: Great Indian Leaders and Freedom Fighters",
         "notes": "Contributions of Mahatma Gandhi, Subhas Chandra Bose, Sardar Patel, and Bhagat Singh."},
        {"ch": "Chapter 12: Social Studies Revision & Practice",
         "notes": "Comprehensive review of Grade 5 geography, history, and civics topics."}
    ],
    "Grade 6": [
        {"ch": "Chapter 1: The Earth in the Solar System",
         "notes": "Planets, stars, satellites, eclipses, and motions of the Earth (rotation and revolution)."},
        {"ch": "Chapter 2: Globe: Latitudes and Longitudes",
         "notes": "Grid systems, standard time zones, and calculating global coordinates."},
        {"ch": "Chapter 3: Motions of the Earth",
         "notes": "Rotation, revolution, equinoxes, and solstices causing seasonal changes."},
        {"ch": "Chapter 4: Maps",
         "notes": "Components of maps (distance, direction, symbol), physical and political maps."},
        {"ch": "Chapter 5: Major Domains of the Earth",
         "notes": "Lithosphere, atmosphere, hydrosphere, and biosphere interactions."},
        {"ch": "Chapter 6: Major Landforms of the Earth",
         "notes": "Mountains, plateaus, plains, and landform land use."},
        {"ch": "Chapter 7: Our Country - India",
         "notes": "Geographical location, neighboring countries, political divisions, and physical features."},
        {"ch": "Chapter 8: India: Climate, Vegetation and Wildlife",
         "notes": "Monsoon seasons, tropical evergreen/deciduous forests, and wildlife conservation."},
        {"ch": "Chapter 9: What, Where, How and When? (History)",
         "notes": "Archaeological sources, manuscripts, inscriptions, and dating historical periods."},
        {"ch": "Chapter 10: From Hunting-Gathering to Growing Food",
         "notes": "Early societies, domestication of plants/animals, and Mehrgarh archaeological site."},
        {"ch": "Chapter 11: In the Earliest Cities (Indus Valley)",
         "notes": "Harappan civilization urban planning, trade, crafts, and decline."},
        {"ch": "Chapter 12: Panchayati Raj & Rural Administration",
         "notes": "Local self-government, gram panchayat, block level administration, and patwari land records."}
    ],
    "Grade 7": [
        {"ch": "Chapter 1: Environment",
         "notes": "Natural and human-made environment, ecosystem dynamics, and ecological balance."},
        {"ch": "Chapter 2: Inside Our Earth & Rocks",
         "notes": "Earth's interior layers, rock types (igneous, sedimentary, metamorphic), and minerals."},
        {"ch": "Chapter 3: Our Changing Earth",
         "notes": "Tectonic plate movements, earthquakes, volcanoes, and river/wind erosional landforms."},
        {"ch": "Chapter 4: Air & Atmospheric Circulation",
         "notes": "Air composition, atmospheric pressure belts, wind systems, and rainfall types."},
        {"ch": "Chapter 5: Water & Ocean Currents",
         "notes": "Distribution of water bodies, ocean tides, and warm/cold ocean currents."},
        {"ch": "Chapter 6: Natural Vegetation and Wildlife",
         "notes": "Forest types around the globe, grasslands, thorny bushes, and wildlife protection."},
        {"ch": "Chapter 7: Human Environment – Settlement, Transport and Communication",
         "notes": "Rural/urban settlements, transport networks, and mass media."},
        {"ch": "Chapter 8: Human Environment Interactions: The Tropical and Subtropical Region",
         "notes": "Amazon basin rainforest life and Ganga-Brahmaputra river basin agriculture."},
        {"ch": "Chapter 9: Life in the Deserts",
         "notes": "Hot desert (Sahara) and cold desert (Ladakh) human adaptations and nomadism."},
        {"ch": "Chapter 10: Tracing Changes Through a Thousand Years (History)",
         "notes": "New and old terminology, regional kingdoms, Delhi Sultanate, and Mughal eras."},
        {"ch": "Chapter 11: New Kings and Kingdoms & Delhi Sultans",
         "notes": "Emergence of new dynasties, Chola empire administration, and Delhi Sultanate rulers."},
        {"ch": "Chapter 12: Equality in Indian Democracy & State Government",
         "notes": "Universal adult franchise, civil rights, and working of state legislative assemblies."}
    ],
    "Grade 8": [
        {"ch": "Chapter 1: Resources and Sustainable Development",
         "notes": "Natural resources, land conservation, water resources, and sustainable development goals."},
        {"ch": "Chapter 2: Land, Soil, Water, Natural Vegetation and Wildlife Resources",
         "notes": "Conservation strategies, soil erosion, and wildlife sanctuaries."},
        {"ch": "Chapter 3: Agriculture and Industries",
         "notes": "Major crop types, shifting cultivation, industrial classifications, and manufacturing hubs."},
        {"ch": "Chapter 4: Human Resources",
         "notes": "Population distribution, density, growth factors, and population pyramids."},
        {"ch": "Chapter 5: How, When and Where (History)",
         "notes": "British colonial rule periodization, official records, and surveys in India."},
        {"ch": "Chapter 6: From Trade to Territory (Company Power)",
         "notes": "East India Company expansion, Battle of Plassey, and subsidiary alliance."},
        {"ch": "Chapter 7: Ruling the Countryside & 1857 Revolt",
         "notes": "Revenue systems (Ryotwari, Mahalwari), indigo cultivation, and the 1857 mutiny."},
        {"ch": "Chapter 8: Colonialism and the City",
         "notes": "Delhi and Calcutta under British urban planning and architectural changes."},
        {"ch": "Chapter 9: Weavers, Iron Smelters and Factory Owners",
         "notes": "Indian textile decline, iron and steel industrialization in Jamshedpur."},
        {"ch": "Chapter 10: Civilising the \"Native\", Educating the Nation",
         "notes": "Orientalist vs anglicist education debate and Macaulay's minute."},
        {"ch": "Chapter 11: Women, Caste and Reform",
         "notes": "Sati abolition, widow remarriage, caste reform movements (Jyotirao Phule, Ambedkar)."},
        {"ch": "Chapter 12: The Indian Constitution & Secularism",
         "notes": "Key features of the Indian Constitution, fundamental rights, and secularism principles."}
    ],
    "Grade 9": [
        {"ch": "Chapter 1: India: Size and Location",
         "notes": "Geographical coordinates, neighboring countries, and strategic peninsular location."},
        {"ch": "Chapter 2: Physical Features of India",
         "notes": "Himalayan mountains, Northern plains, Peninsular plateau, coastal plains, and islands."},
        {"ch": "Chapter 3: Drainage (River Systems)",
         "notes": "Himalayan vs peninsular rivers, river basins, and river pollution/conservation."},
        {"ch": "Chapter 4: Climate",
         "notes": "Monsoon onset mechanism, climatic controls, seasons, and distribution of rainfall."},
        {"ch": "Chapter 5: Natural Vegetation and Wildlife",
         "notes": "Forest types in India, medicinal plants, and wildlife sanctuaries."},
        {"ch": "Chapter 6: Population",
         "notes": "Population size, distribution, growth, literacy rates, and national health policy."},
        {"ch": "Chapter 7: The French Revolution",
         "notes": "Causes of the revolution, fall of Bastille, reign of terror, and rise of Napoleon."},
        {"ch": "Chapter 8: Socialism in Europe and the Russian Revolution",
         "notes": "February and October revolutions, formation of the USSR, and Stalin's collectivization."},
        {"ch": "Chapter 9: Nazism and the Rise of Hitler",
         "notes": "Weimar republic, Hitler's rise to power, racial ideology, and Holocaust horrors."},
        {"ch": "Chapter 10: Forest Society and Colonialism",
         "notes": "Deforestation under British rule, scientific forestry, and Bastar tribal rebellion."},
        {"ch": "Chapter 11: Pastoralists in the Modern World",
         "notes": "Nomadic pastoralism in Africa and India under colonial grazing laws."},
        {"ch": "Chapter 12: Democratic Politics & Constitutional Design",
         "notes": "Democratic principles, constituent assembly, electoral politics, and working of institutions."}
    ],
    "Grade 10": [
        {"ch": "Chapter 1: Resources and Development",
         "notes": "Resource planning, soil types, land degradation, and conservation."},
        {"ch": "Chapter 2: Forest and Wildlife Resources",
         "notes": "Flora and fauna depletion, Project Tiger, and joint forest management."},
        {"ch": "Chapter 3: Water Resources",
         "notes": "Multipurpose river projects, dams controversy, and rainwater harvesting."},
        {"ch": "Chapter 4: Agriculture",
         "notes": "Types of farming, cropping seasons, major crops, and technological reforms."},
        {"ch": "Chapter 5: Minerals and Energy Resources",
         "notes": "Metallic/non-metallic minerals, conventional and non-conventional energy sources."},
        {"ch": "Chapter 6: Manufacturing Industries",
         "notes": "Industrial location factors, agro-based and mineral-based industries, and pollution."},
        {"ch": "Chapter 7: Lifelines of National Economy",
         "notes": "Transport networks, international trade, and tourism as trade."},
        {"ch": "Chapter 8: The Rise of Nationalism in Europe",
         "notes": "French revolution, unification of Italy and Germany, and Balkan nationalism."},
        {"ch": "Chapter 9: Nationalism in India",
         "notes": "Non-Cooperation movement, Civil Disobedience, salt march, and freedom struggle milestones."},
        {"ch": "Chapter 10: The Making of a Global World",
         "notes": "Silk routes, nineteenth-century global economy, Great Depression, and post-war recovery."},
        {"ch": "Chapter 11: Print Culture and the Modern World",
         "notes": "First printed books in China/Europe, print revolution in India, and censorship."},
        {"ch": "Chapter 12: Federalism, Democracy and Political Parties",
         "notes": "Federal structures, decentralization in India, political parties, and outcomes of democracy."}
    ]
}

ENGLISH_SYLLABUS_DATABASE = {
    "Grade 5": [
        {"ch": "Chapter 1: Prose - The Magic Garden",
         "notes": "A story about a magic garden in a school playground where children played with flowers and fairies."},
        {"ch": "Chapter 2: Poem - Bird Talk",
         "notes": "A conversation between two little birds about how humans differ from them."},
        {"ch": "Chapter 3: Prose - Run!",
         "notes": "An energetic poem encouraging children to run out towards the country, away from the city."},
        {"ch": "Chapter 4: Grammar - Nouns & Pronouns",
         "notes": "Understanding common, proper, and collective nouns along with personal pronouns."},
        {"ch": "Chapter 5: Prose - My Shadow",
         "notes": "Exploring the funny habits of a shadow that grows taller and smaller unexpectedly."},
        {"ch": "Chapter 6: Grammar - Verbs & Tenses",
         "notes": "Simple present, past, and future tense verbs with subject-verb agreement."},
        {"ch": "Chapter 7: Prose - Robinson Crusoe",
         "notes": "Discovering a footprint on the sand and the adventure of survival on an island."},
        {"ch": "Chapter 8: Poem - Crying",
         "notes": "Understanding that crying helps release sorrow before finding happiness again."},
        {"ch": "Chapter 9: Grammar - Adjectives & Adverbs",
         "notes": "Describing words and modifiers to make sentences more expressive."},
        {"ch": "Chapter 10: Prose - The Talkative Barber",
         "notes": "A humorous tale of a talkative barber and a sultan in ancient Baghdad."},
        {"ch": "Chapter 11: Writing - Letter and Paragraph Writing",
         "notes": "Formal/informal letters and creative paragraph structuring."},
        {"ch": "Chapter 12: Comprehensive English Practice",
         "notes": "Revision of reading comprehension, vocabulary, and grammar rules."}
    ],
    "Grade 6": [
        {"ch": "Chapter 1: Who Did Patrick's Homework?",
         "notes": "A story about a lazy boy who gets help from a tiny elf to complete his school assignments."},
        {"ch": "Chapter 2: How the Dog Found Himself a Master",
         "notes": "A folk tale tracing how dogs evolved from wild animals to loyal human companions."},
        {"ch": "Chapter 3: Taro's Reward",
         "notes": "A Japanese story about a filial son whose love for his parents is rewarded by a magical waterfall."},
        {"ch": "Chapter 4: An Indian-American Woman in Space: Kalpana Chawla",
         "notes": "The inspiring life journey of astronaut Kalpana Chawla from Karnal to NASA."},
        {"ch": "Chapter 5: A Different Kind of School",
         "notes": "A visit to a school that teaches empathy by blindfolding and immobilizing students for a day."},
        {"ch": "Chapter 6: Who I Am",
         "notes": "Diverse students expressing their unique dreams, personalities, and aspirations."},
        {"ch": "Chapter 7: Fair Play",
         "notes": "A moral story about friendship, justice, and truth starring Algu Choudhary and Jumman Sheikh."},
        {"ch": "Chapter 8: A Game of Chance",
         "notes": "An Eid fair experience illustrating how greed and temptation can lead to disappointment."},
        {"ch": "Chapter 9: Desert Animals",
         "notes": "Fascinating adaptations of camels, gerbils, and desert snakes surviving harsh climates."},
        {"ch": "Chapter 10: The Banyan Tree",
         "notes": "A thrilling battle between a mongoose and a cobra witnessed from an old banyan tree."},
        {"ch": "Chapter 11: Grammar & Advanced Vocabulary",
         "notes": "Active/passive voice basics, punctuation, prefixes, and suffixes."},
        {"ch": "Chapter 12: Creative Writing & Comprehension",
         "notes": "Story writing, essay composition, and unseen passage exercises."}
    ],
    "Grade 7": [
        {"ch": "Chapter 1: Three Questions",
         "notes": "A king seeks answers to three crucial life questions from a wise hermit."},
        {"ch": "Chapter 2: A Gift of Chappals",
         "notes": "A heartwarming story of children showing compassion to a struggling street musician."},
        {"ch": "Chapter 3: Gopal and the Hilsa-Fish",
         "notes": "A clever courtier pulls off a bizarre challenge to prove people can be distracted from foolish talk."},
        {"ch": "Chapter 4: The Ashes That Made Trees Bloom",
         "notes": "A Japanese fable about a faithful dog, kind owners, and wicked neighbors."},
        {"ch": "Chapter 5: Quality",
         "notes": "A poignant tale about a German shoemaker dedicated to perfection and true craftsmanship."},
        {"ch": "Chapter 6: Expert Detectives",
         "notes": "Two siblings investigating a mysterious, reclusive man they suspect of being a crook."},
        {"ch": "Chapter 7: The Invention of Vita-Wonk",
         "notes": "Mr. Willy Wonka embarks on a fantastical journey creating a time-reversing potion."},
        {"ch": "Chapter 8: Fire: Friend and Foe",
         "notes": "The science of fire, how it is controlled, and its dual nature as helper and hazard."},
        {"ch": "Chapter 9: A Bicycle in Good Repair",
         "notes": "A humorous account of an unnecessary and destructive bicycle servicing."},
        {"ch": "Chapter 10: The Story of Cricket",
         "notes": "Historical origins, equipment evolution, and global cultural impact of cricket."},
        {"ch": "Chapter 11: Advanced Grammar & Syntax", "notes": "Reported speech, modals, clauses, and determiners."},
        {"ch": "Chapter 12: Essay & Letter Composition",
         "notes": "Formal email writing, article drafting, and literary analysis."}
    ],
    "Grade 8": [
        {"ch": "Chapter 1: The Best Christmas Present in the World",
         "notes": "An emotional letter found in an old roll-top desk recounting a WWI Christmas truce."},
        {"ch": "Chapter 2: The Tsunami",
         "notes": "Survival accounts and heroic acts during the devastating 2004 Indian Ocean tsunami."},
        {"ch": "Chapter 3: Glimpses of the Past",
         "notes": "Pictorial snapshots of Indian history from 1757 to the 1857 freedom struggle."},
        {"ch": "Chapter 4: Bepin Choudhury's Lapse of Memory",
         "notes": "A psychological mystery surrounding a man who cannot recall visiting Ranchi."},
        {"ch": "Chapter 5: The Summit Within",
         "notes": "Major H.P.S. Ahluwalia reflects on the physical and spiritual climbing of Mount Everest."},
        {"ch": "Chapter 6: This is Jody's Fawn",
         "notes": "A young boy takes moral responsibility for nursing an orphaned fawn back to health."},
        {"ch": "Chapter 7: A Visit to Cambridge",
         "notes": "A moving conversation between writer Firdaus Kanga and the brilliant physicist Stephen Hawking."},
        {"ch": "Chapter 8: A Short Monsoon Diary",
         "notes": "Ruskin Bond's journal entries detailing mist, wildlife, and tranquility in the hills."},
        {"ch": "Chapter 9: The Great Stone Face",
         "notes": "A prophecy about a local valley resident resembling a majestic natural mountain rock formation."},
        {"ch": "Chapter 10: Advanced Grammar & Composition",
         "notes": "Non-finite verbs, conjunctions, voice transformation, and sentence synthesis."},
        {"ch": "Chapter 11: Critical Reading & Appreciation",
         "notes": "Analyzing poetic devices, metaphors, and prose themes."},
        {"ch": "Chapter 12: Creative Writing Masterclass",
         "notes": "Debate speeches, formal reports, and descriptive writing portfolios."}
    ],
    "Grade 9": [
        {"ch": "Chapter 1: The Fun They Had",
         "notes": "A futuristic sci-fi story set in 2157 comparing robotic schooling to printed books."},
        {"ch": "Chapter 2: The Sound of Music",
         "notes": "Biographical profiles of deaf percussionist Evelyn Glennie and classical maestro Bismillah Khan."},
        {"ch": "Chapter 3: The Little Girl",
         "notes": "Kezia's shifting perception of her strict father from fear to deep understanding."},
        {"ch": "Chapter 4: A Truly Beautiful Mind",
         "notes": "The extraordinary scientific career and humanitarian philosophy of Albert Einstein."},
        {"ch": "Chapter 5: The Snake and the Mirror",
         "notes": "A humorous homeopathic doctor's encounter with a deadly cobra coiled around his arm."},
        {"ch": "Chapter 6: My Childhood",
         "notes": "APJ Abdul Kalam's early life in Rameswaram, formative friendships, and scientific curiosity."},
        {"ch": "Chapter 7: Packing",
         "notes": "Jerome K. Jerome's hilarious description of chaotic suitcase packing with friends."},
        {"ch": "Chapter 8: Reach for the Top",
         "notes": "Inspirational accounts of mountaineers Santosh Yadav and Maria Sharapova."},
        {"ch": "Chapter 9: The Bond of Love",
         "notes": "An affectionate bond between a sloth bear named Bruno and a wildlife conservationist family."},
        {"ch": "Chapter 10: Kathmandu",
         "notes": "Vikram Seth's vivid travelogue contrasting the bustling Pashupatinath temple and Boudhanath stupa."},
        {"ch": "Chapter 11: Advanced English Grammar",
         "notes": "Subject-verb concord, reported speech, clauses, and determiners."},
        {"ch": "Chapter 12: Literary Analysis & Writing",
         "notes": "Diary entry composition, story writing from outlines, and critical analysis."}
    ],
    "Grade 10": [
        {"ch": "Chapter 1: A Letter to God",
         "notes": "Lencho's profound faith in divine help after a devastating hailstorm ruins his corn crop."},
        {"ch": "Chapter 2: Nelson Mandela: Long Walk to Freedom",
         "notes": "Mandela's historic inauguration speech celebrating the end of apartheid in South Africa."},
        {"ch": "Chapter 3: Two Stories about Flying",
         "notes": "A young seagull overcoming his fear of flight and a pilot guided through a mysterious storm."},
        {"ch": "Chapter 4: From the Diary of Anne Frank",
         "notes": "Excerpts from Anne Frank's wartime diary describing her isolation and thoughts in hiding."},
        {"ch": "Chapter 5: Glimpses of India",
         "notes": "Cultural snapshots of Goan bakers, Coorg coffee plantations, and Assamese tea gardens."},
        {"ch": "Chapter 6: Mijbil the Otter",
         "notes": "Gavin Maxwell's adventures transporting and raising an unusual pet otter from Iraq to London."},
        {"ch": "Chapter 7: Madam Rides the Bus",
         "notes": "An eight-year-old girl named Valli fulfills her deep desire to take a solo bus ride."},
        {"ch": "Chapter 8: The Sermon at Benares",
         "notes": "Gautama Buddha's teachings on mortal grief and the universal acceptance of death."},
        {"ch": "Chapter 9: The Proposal",
         "notes": "Anton Chekhov's classic one-act farce about neighbors arguing over land before proposing marriage."},
        {"ch": "Chapter 10: Advanced Grammar & Functional English",
         "notes": "Integrated grammar edits, omissions, gap filling, and sentence transformations."},
        {"ch": "Chapter 11: Analytical Paragraph & Report Writing",
         "notes": "Interpreting charts, graphs, data cues into formal descriptive essays."},
        {"ch": "Chapter 12: Literature Review & Sample Test Papers",
         "notes": "Comprehensive practice across prose, poetry, foot-prints without feet, and board exams."}
    ]
}

TELUGU_SYLLABUS_DATABASE = {
    "Grade 5": [
        {"ch": "Chapter 1: దేశభక్తి (Desabhakti)",
         "notes": "ప్రాచీన మరియు ఆధునిక దేశభక్తి గీతాలు, మాతృభూమి గొప్పతనం మరియు జాతీయ భావాలు."},
        {"ch": "Chapter 2: మాతృమూర్తి (Matrumurthi)",
         "notes": "తల్లి ప్రేమ, కుటుంబ విలువలు మరియు బాల్యంలో నేర్చుకోవాల్సిన మంచి అలవాట్లు."},
        {"ch": "Chapter 3: మన పండుగలు (Mana Pandugalu)",
         "notes": "తెలుగు సంస్కృతి, సంప్రదాయాలు మరియు ఉగాది, సంక్రాంతి వంటి ప్రధాన పండుగ విశేషాలు."},
        {"ch": "Chapter 4: శతక సుధ (Sataka Sudha)", "notes": "వేమన, సుమతీ శతకాలలోని నీతి పద్యాలు మరియు వాటి భావాలు."},
        {"ch": "Chapter 5: బాలల హక్కులు (Balala Hakkulu)",
         "notes": "పిల్లల హక్కులు, విద్య ప్రాముఖ్యత మరియు మంచి పౌరులుగా ఎదగడం."},
        {"ch": "Chapter 6: ప్రకృతి వనరులు (Prakruthi Vanarulu)",
         "notes": "చెట్లు, నీరు, పక్షులు మరియు పర్యావరణ పరిరక్షణ అవసరం."},
        {"ch": "Chapter 7: తెలుగు భాషా గొప్పతనం (Telugu Bhasha Goppatanam)",
         "notes": "ఇటాలియన్ ఆఫ్ ది ఈస్ట్ గా పిలువబడే తెలుగు భాషా మాధుర్యం మరియు సాహిత్యం."},
        {"ch": "Chapter 8: విజ్ఞాన శాస్త్ర వింతలు (Vignana Sastra Vintalu)",
         "notes": "శాస్త్ర సాంకేతిక పరిజ్ఞానం మరియు దైనందిన జీవితంలో సైన్స్ పాత్ర."},
        {"ch": "Chapter 9: సత్ప్రవర్తన (Satpravartana)",
         "notes": "పెద్దలను గౌరవించడం, నిజాయితీ మరియు తోటివారికి సహాయం చేయడం."},
        {"ch": "Chapter 10: జాతీయ నాయకులు (Jాతీయ నాయకులు - Leaders)",
         "notes": "మహాత్మా గాంధీ, అల్లూరి సీతారామరాజు వంటి స్వాతంత్ర్య సమరయోధుల జీవిత విశేషాలు."},
        {"ch": "Chapter 11: వ్యాకరణం & పదజాలం (Vyakaranam)",
         "notes": "నామవాచకం, సర్వనామం, అర్థాలు, పర్యాయపదాలు మరియు వ్యతిరేక పదాలు."},
        {"ch": "Chapter 12: పునశ్చరణ & అంచనా పత్రాలు (Revision)",
         "notes": "ఐదవ తరగతి తెలుగు సిలబస్ పూర్తి పునశ్చరణ మరియు అభ్యాస ప్రశ్నలు."}
    ],
    "Grade 6": [
        {"ch": "Chapter 1: మా కొద్ది తెల్లదొరతనం (Maa Koddi Telladoratanam)",
         "notes": "స్వాతంత్ర్య ఉద్యమ కాలంలో తెలుగు ప్రజల దేశభక్తి మరియు గాంధేయవాద పోరాటాలు."},
        {"ch": "Chapter 2: త్యాగనిరతి (Tyaganirati)",
         "notes": "సిబి చక్రవర్తి కథ ద్వారా ప్రాణ త్యాగం, శరణాగత రక్షణ మరియు ధర్మం యొక్క గొప్పతనం."},
        {"ch": "Chapter 3: రాళ్లలో తేలే కమలాలు (Kamalalu)",
         "notes": "కఠిన పరిస్థితులలో కూడా చదువులో రాణించే పిల్లల స్పూర్తిదాయక గాథలు."},
        {"ch": "Chapter 4: శతక మధురిమ (Sataka Madhurima)", "notes": "భర్తృహరి, వేమన శతక పద్యాలు మరియు నైతిక విలువలు."},
        {"ch": "Chapter 5: ఉగాది (Ugadi)",
         "notes": "తెలుగు సంవత్సరది విశిష్టత, షడ్రుచుల సమ్మేళనం మరియు ప్రకృతిలో వచ్చే మార్పులు."},
        {"ch": "Chapter 6: యక్షప్రశ్నలు (Yakshaprashnalu)",
         "notes": "మహాభారతంలోని ధర్మరాజు మరియు యక్షుని మధ్య జరిగిన తత్వసంబంధిత సంభాషణలు."},
        {"ch": "Chapter 7: జానపద కళలు (Janapada Kalalu)",
         "notes": "బతుకమ్మ, వీరనాట్యం, కొమ్ముకోలాటం వంటి ఆంధ్రప్రదేశ్ జానపద కళారూపాలు."},
        {"ch": "Chapter 8: మొక్కల పెంపకం (Mokkula Pempakam)",
         "notes": "హరితహారం, వృక్షో రక్షతి రక్షితః సందేశం మరియు మొక్కల వల్ల ప్రయోజనాలు."},
        {"ch": "Chapter 9: బాల గాంధీ (Bala Gandhi)", "notes": "మహాత్మా గాంధీ బాల్యంలో జరిగిన సంఘటనలు మరియు సత్యనిష్ఠ."},
        {"ch": "Chapter 10: తెలుగు జాతీయాలు & సామెతలు (Idioms & Proverbs)",
         "notes": "తెలుగు భాషలోని జాతీయాలు, సామెతలు వాటి అర్థాలు మరియు ప్రయోగాలు."},
        {"ch": "Chapter 11: వ్యాకరణ విశేషాలు (Vyakaranam)",
         "notes": "సంధులు (సవర్ణదీర్ఘ, గుణ, వృద్ధి), సమాసాలు మరియు అలంకారాలు."},
        {"ch": "Chapter 12: పరీక్షా విధానం & అభ్యాసాలు (Revision)",
         "notes": "ఆరవ తరగతి తెలుగు పాఠ్యభాగాల సమగ్ర పునశ్చరణ."}
    ],
    "Grade 7": [
        {"ch": "Chapter 1: చైతన్య స్ఫూర్తి (Chaitanya Spoorti)",
         "notes": "యువతలో మానసిక స్థైర్యం, నాయకత్వ లక్షణాలు మరియు సమాజ సేవా దృక్పథం."},
        {"ch": "Chapter 2: శీల పరీక్ష (Sheela Pareeksha)",
         "notes": "రామాయణం ఆధారంగా సత్యసంధత, ధర్మపాలన మరియు నైతిక ప్రవర్తన."},
        {"ch": "Chapter 3: అమరావతి (Amaravati)",
         "notes": "ఆంధ్రప్రదేశ్ చారిత్రక రాజధాని అమరావతి యొక్క బౌద్ధ వారసత్వం మరియు శిల్పకళా వైభవం."},
        {"ch": "Chapter 4: శతక సుధలు (Sataka Sudhalu)", "notes": "దాశరథీ, సుమతీ శతకాల నుండి నీతి బోధనలు."},
        {"ch": "Chapter 5: శ్రమయేవ జయతే (Shramayeva Jayate)",
         "notes": "కష్టపడి పనిచేయడం వల్ల కలిగే ఫలితం మరియు శ్రమయొక్క గొప్పతనం."},
        {"ch": "Chapter 6: మేలుకొలుపు (Melukolupu)", "notes": "సమాజంలో చైతన్యం తేవడానికి కవులు అందించిన సందేశాలు."},
        {"ch": "Chapter 7: రుద్రమదేవి (Rudramadevi)",
         "notes": "కాకతీయ సామ్రాజ్య వీరనారి రాణి రుద్రమదేవి పాలనా సామర్థ్యం మరియు సాహసాలు."},
        {"ch": "Chapter 8: ఆరోగ్యం - వ్యాయాయం (Health & Exercise)",
         "notes": "ఆరోగ్యమే మహాభాగ్యం, యోగా మరియు క్రమశిక్షణతో కూడిన జీవనశైలి."},
        {"ch": "Chapter 9: అభ్యుదయ కవితలు (Abhyudaya Kavitalu)",
         "notes": "సమాజంలోని అసమానతలను రూపుమాపడానికి కవుల కవితా గళం."},
        {"ch": "Chapter 10: తెలుగు పత్రికలు (Telugu Patrikalu)",
         "notes": "తెలుగు పాత్రికేయ చరిత్ర మరియు ప్రముఖ పత్రికల పాత్ర."},
        {"ch": "Chapter 11: తెలుగు వ్యాకరణం (Advanced Vyakaranam)",
         "notes": "ఉత్పలమాల, చంపకమాల వంటి వృత్త జాతి పద్య లక్షణాలు."},
        {"ch": "Chapter 12: వార్షిక పునశ్చరణ (Annual Revision)", "notes": "ఏడవ తరగతి తెలుగు సమగ్ర అభ్యాస పత్రాలు."}
    ],
    "Grade 8": [
        {"ch": "Chapter 1: వేదం (Vedam / చైతన్యం)",
         "notes": "భారతీయ సనాతన సంస్కృతిలో వేదాల ప్రాముఖ్యత మరియు విజ్ఞానం."},
        {"ch": "Chapter 2: శరపంజరం (Sharapanjaram)", "notes": "మహాభారతంలోని భీష్ముని పాత్ర మరియు ధర్మసూక్ష్మాలు."},
        {"ch": "Chapter 3: గోల్కొండ పట్టణం (Golconda Patnam)",
         "notes": "కుతుబ్‌షాహీల కాలం నాటి గోల్కొండ కోట చరిత్ర మరియు వజ్రాల వ్యాపారం."},
        {"ch": "Chapter 4: భక్తి సుధ (Bhakti Sudha)", "notes": "భక్త కవుల కీర్తనలు మరియు భక్తి తత్వం."},
        {"ch": "Chapter 5: యంత్రాల సహాయం (Yantrala Sahayam)",
         "notes": "ఆధునిక సాంకేతికత మరియు మానవ జీవితంపై యంత్రాల ప్రభావం."},
        {"ch": "Chapter 6: భగత్ సింగ్ (Bhagat Singh)",
         "notes": "భారత స్వాతంత్ర్య సమరంలో అమరవీరుడు భగత్ సింగ్ త్యాగం మరియు దేశభక్తి."},
        {"ch": "Chapter 7: రక్షించుకుందాం (Rakshinchukundam)", "notes": "పర్యావరణ పరిరక్షణ, అడవుల నరికివేత నివారణ."},
        {"ch": "Chapter 8: వీర తెలంగాణ (Veera Telangana)",
         "notes": "తెలంగాణ సాయుధ పోరాటంలో రైతుల విప్లవం మరియు వీరత్వం."},
        {"ch": "Chapter 9: హ్రదయం (Hridayam)", "notes": "మానవతా విలువలు, తోటివారి పట్ల ప్రేమ మరియు కరుణ."},
        {"ch": "Chapter 10: శతక సౌరభం (Sataka Sourabham)", "notes": "వివిధ శతకాల నుండి నైతిక విలువలు నేర్పే పద్యాలు."},
        {"ch": "Chapter 11: తెలుగు వ్యాకరణం (Grammar & Prosody)", "notes": "సంధులు, సమాసాలు, అలంకారాలు మరియు ఛందస్సు."},
        {"ch": "Chapter 12: పరీక్షా సమాయత్తత (Exam Practice)",
         "notes": "ఎనిమిదవ తరగతి తెలుగు మోడల్ పేపర్స్ మరియు రివిజన్."}
    ],
    "Grade 9": [
        {"ch": "Chapter 1: ధర్మజుని వాక్చాతుర్యం (Dharmajuni Vakchaturyam)",
         "notes": "మహాభారత యుద్ధ పూర్వ రంగంలో రాయబారం మరియు ధర్మరాజు మాటతీరు."},
        {"ch": "Chapter 2: శతక మధురిమలు (Sataka Madhurimalu)",
         "notes": "సజ్జనుల లక్షణాలు, లోకరీతి మరియు నైతిక సూత్రాలు."},
        {"ch": "Chapter 3: సీత ఇష్టాలు (Seeta Ishtalu)",
         "notes": "రామాయణంలో ప్రకృతితో సీతాదేవి అనుబంధం మరియు జీవన శైలి."},
        {"ch": "Chapter 4: భిక్ష (Bhiksha)", "notes": "గురుదక్షిణ మరియు దానధర్మాల ప్రాముఖ్యతను తెలిపే ఇతివృత్తం."},
        {"ch": "Chapter 5: శిల్పి (Silpi)",
         "notes": "గుర్తుండిపోయే శిల్పాలను చెక్కే శిల్పి పడే శ్రమ మరియు కళా తపస్సు."},
        {"ch": "Chapter 6: ఏ దేశమేగినా (Ae Desamegina)",
         "notes": "రాయప్రోలు సుబ్బారావు గారి దేశభక్తి గీతం మరియు విశ్వమానవ సౌభ్రాతృత్వం."},
        {"ch": "Chapter 7: బలిదానం (Balidanam)", "notes": "దేశం కోసం ప్రాణాలర్పించిన వీరుల త్యాగ నిరతి."},
        {"ch": "Chapter 8: గోదావరి (Godavari River)",
         "notes": "దక్షిణ భారతదేశ గంగగా పిలువబడే గోదావరి నది ప్రాముఖ్యత మరియు సంస్కృతి."},
        {"ch": "Chapter 9: అభ్యుదయం (Abhyudayam)", "notes": "సమాజంలో మార్పుకోసం యువత చేయవలసిన పోరాటాలు."},
        {"ch": "Chapter 10: జాతీయ కవులు (National Poets)",
         "notes": "తెలుగు సాహిత్యానికి కవులు అందించిన అమూల్యమైన సేవలు."},
        {"ch": "Chapter 11: ఆధునిక వ్యాకరణం (Advanced Grammar)",
         "notes": "ఉపసర్గలు, ప్రత్యయాలు, వాక్య నిర్మాణం మరియు సంధి కార్యాలు."},
        {"ch": "Chapter 12: సమగ్ర పునశ్చరణ (Comprehensive Revision)",
         "notes": "తొమ్మిదవ తరగతి తెలుగు పూర్తి సిలబస్ పరీక్షా అభ్యాసాలు."}
    ],
    "Grade 10": [
        {"ch": "Chapter 1: దాన వీర సూర కర్ణ (Dana Veera Sura Karna)",
         "notes": "మహాభారతంలో కర్ణుని దాతృత్వం మరియు కుల మతాలతీసి కర్ణుడు చూపిన మానవత్వం."},
        {"ch": "Chapter 2: దేశభక్తి (Desabhakti)",
         "notes": "శ్రీశ్రీ మరియు గుర్రం జాషువా కవితల ద్వారా సమ సమాజ స్థాపన మరియు దేశభక్తి."},
        {"ch": "Chapter 3: లక్ష్మణ రేఖ (Lakshmana Rekha)",
         "notes": "జీవితంలో ప్రతి మనిషి పాటించవలసిన నియమాలు మరియు నైతిక హద్దులు."},
        {"ch": "Chapter 4: భక్తి ప్రపత్తులు (Bhakti Prapatthulu)",
         "notes": "భక్తి ఉద్యమం మరియు తెలుగు సాహిత్యంలో భక్తి తత్వం."},
        {"ch": "Chapter 5: శతక సుధ (Sataka Sudha)",
         "notes": "పదమూడు శతకాల నుండి జీవిత సత్యాలను బోధించే శ్రేష్టమైన పద్యాలు."},
        {"ch": "Chapter 6: మాతృభాష (Mother Tongue Importance)",
         "notes": "మాతృభాషలోనే ప్రాథమిక విద్య మరియు మాతృభాషాభిమానం ప్రాముఖ్యత."},
        {"ch": "Chapter 7: శిల్ప కళా వైభవం (Art & Architecture)",
         "notes": "కాకతీయ శిల్పకళ, రామప్ప దేవాలయం మరియు చారిత్రక కట్టడాలు."},
        {"ch": "Chapter 8: స్వామి వివేకానంద (Swami Vivekananda)",
         "notes": "వివేకానంద బోధనలు, యువతకు ఆయన ఇచ్చిన పిలుపు మరియు ఆత్మవిశ్వాసం."},
        {"ch": "Chapter 9: తెలుగు సాహిత్య చరిత్ర (Telugu Literature History)",
         "notes": "నన్నయ్య కాలం నుండి ఆధునిక కాలం వరకు తెలుగు సాహిత్య పరిణామ క్రమం."},
        {"ch": "Chapter 10: వ్యాకరణం & ఛందస్సు (Grammar & Metre)",
         "notes": "ఉత్పలమాల, చంపకమాల, శార్దూలం, మత్తేభం మరియు అలంకారాలు."},
        {"ch": "Chapter 11: లేఖలు & వ్యాస రచన (Letter & Essay Writing)",
         "notes": "అధికారులకు లేఖలు, సంపాదకీయాలు మరియు సమకాలీన అంశాలపై వ్యాసాలు."},
        {"ch": "Chapter 12: పదవ తరగతి బోర్డు పరీక్షల మాదిరి పత్రాలు (Board Exam Practice)",
         "notes": "పదవ తరగతి పబ్లిక్ పరీక్షల సిలబస్ ప్రకారం మోడల్ క్వశ్చన్ పేపర్స్."}
    ]
}


# Quiz Generator supporting all subjects
def generate_20_questions(grade, chapter, subject, difficulty):
    questions = []
    prefix = f"[{difficulty} Tier] "
    ch_lower = chapter.lower()
    sub_lower = subject.lower()

    for i in range(1, 21):
        if "science" in sub_lower:
            if i % 3 == 0:
                q_text = f"{prefix}Q{i}: Which of the following is an essential requirement for photosynthesis in green plants?"
                options = ["Chlorophyll and Sunlight", "Carbon Dioxide only", "Oxygen and Nitrogen", "Darkness"]
                answer = "Chlorophyll and Sunlight"
            elif i % 3 == 1:
                q_text = f"{prefix}Q{i}: What is the basic structural and functional unit of all living organisms?"
                options = ["Cell", "Tissue", "Organ", "Atom"]
                answer = "Cell"
            else:
                q_text = f"{prefix}Q{i}: Which force is responsible for opposing relative motion between two surfaces in contact?"
                options = ["Friction", "Gravity", "Magnetism", "Tension"]
                answer = "Friction"
            random.shuffle(options)
            questions.append({"question": q_text, "options": options, "answer": answer})

        elif "social" in sub_lower or "sst" in sub_lower:
            if i % 3 == 0:
                q_text = f"{prefix}Q{i}: Which imaginary line divides the Earth into the Northern and Southern Hemispheres?"
                options = ["Equator", "Prime Meridian", "Tropic of Cancer", "International Date Line"]
                answer = "Equator"
            elif i % 3 == 1:
                q_text = f"{prefix}Q{i}: What is the primary source of energy driving the Earth's weather and climate systems?"
                options = ["The Sun", "Geothermal Core", "Ocean Currents", "Wind Turbines"]
                answer = "The Sun"
            else:
                q_text = f"{prefix}Q{i}: Which branch of government is primarily responsible for enacting and passing laws?"
                options = ["Legislature", "Executive", "Judiciary", "Police Department"]
                answer = "Legislature"
            random.shuffle(options)
            questions.append({"question": q_text, "options": options, "answer": answer})

        elif "english" in sub_lower:
            if i % 3 == 0:
                q_text = f"{prefix}Q{i}: Identify the part of speech for the capitalized word in: 'The brave SOLDIER fought well.'"
                options = ["Noun", "Verb", "Adjective", "Adverb"]
                answer = "Noun"
            elif i % 3 == 1:
                q_text = f"{prefix}Q{i}: Choose the correct past tense form of 'run':"
                options = ["Ran", "Running", "Runned", "Runs"]
                answer = "Ran"
            else:
                q_text = f"{prefix}Q{i}: What is a synonym of the word 'Courage'?"
                options = ["Bravery", "Cowardice", "Fear", "Weakness"]
                answer = "Bravery"
            random.shuffle(options)
            questions.append({"question": q_text, "options": options, "answer": answer})

        elif "telugu" in sub_lower:
            if i % 3 == 0:
                q_text = f"{prefix}Q{i}: 'సూర్యుడు' పదానికి పర్యాయపదం కానిది ఏది?"
                options = ["భాస్కరుడు", "రవి", "చంద్రుడు", "దినకరుడు"]
                answer = "చంద్రుడు"
            elif i % 3 == 1:
                q_text = f"{prefix}Q{i}: 'పుస్తకం' అనేది ఏ రకమైన శబ్దం / పదం?"
                options = ["నామవాచకం", "సర్వనామం", "క్రియ", "విశేషణం"]
                answer = "నామవాచకం"
            else:
                q_text = f"{prefix}Q{i}: 'సత్యం' పదానికి వ్యతిరేక పదం ఏమిటి?"
                options = ["అసత్యం", "నిజం", "ధర్మం", "పాపం"]
                answer = "అసత్యం"
            random.shuffle(options)
            questions.append({"question": q_text, "options": options, "answer": answer})

        else:
            if "geometry" in ch_lower or "shape" in ch_lower or "angle" in ch_lower or "triangle" in ch_lower:
                problem, answer = mg.third_angle_of_triangle()
            elif "fraction" in ch_lower or "decimal" in ch_lower:
                problem, answer = mg.fraction_addition()
            elif "factor" in ch_lower or "multiple" in ch_lower or "lcm" in ch_lower:
                problem, answer = mg.lcm()
            elif "algebra" in ch_lower or "equation" in ch_lower or "polynomial" in ch_lower:
                problem, answer = mg.basic_algebra()
            else:
                problem, answer = mg.addition()

            q_text = f"{prefix}Q{i}: {problem}"
            try:
                ans_float = float(str(answer).replace('$', '').replace('\\', ''))
                options = [str(answer), f"${ans_float + 5}$", f"${ans_float - 3}$", f"${ans_float + 10}$"]
            except ValueError:
                options = [str(answer), "Option A", "Option B", "Option C"]
            random.shuffle(options)
            questions.append({"question": q_text, "options": options, "answer": str(answer)})

    return questions


# ---------------------------------------------------------
# PAGE FLOW ROUTING
# ---------------------------------------------------------

# 1. LOGIN / ROLE SELECTION PAGE
if st.session_state.current_page == "login":
    st.markdown("""
        <div class="header-card">
            <h1>🎓 Skill Nest Portal</h1>
            <p>AP State Syllabus Learning Companion (Grades 5 to 10 - Math, Science, SST, English & Telugu)</p>
        </div>
    """, unsafe_allow_html=True)

    portal_role = st.selectbox("Select Portal Access:", ["Student Portal", "Teacher Administration Portal"])
    st.divider()

    if portal_role == "Student Portal":
        st.subheader("Student Login")
        username = st.text_input("Full Name")
        student_email = st.text_input("Login Code")
        phone = st.text_input("Phone Number (e.g., +91 9876543210)")
        selected_grade = st.selectbox("Select Grade",
                                      ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"])

        if st.button("Continue to Phone Code Verification ➔"):
            if username and student_email and phone:
                st.session_state.user = username.strip()
                st.session_state.email = student_email.strip()
                st.session_state.phone = phone
                st.session_state.grade = selected_grade

                clean_name = "".join(e for e in st.session_state.user if e.isalnum()).capitalize()
                if not clean_name:
                    clean_name = "Student"
                rand_digits = str(random.randint(100, 999))
                st.session_state.student_id = f"{clean_name}{rand_digits}"

                if st.session_state.email in db["registered_students"]:
                    existing_record = db["registered_students"][st.session_state.email]
                    st.session_state.plan = existing_record["plan"]
                    st.session_state.student_id = existing_record["student_id"]
                    st.session_state.grade = existing_record["grade"]

                st.session_state.otp_code = str(random.randint(1000, 9999))
                st.session_state.current_page = "security_checkup"
                st.rerun()
            else:
                st.error("Please enter your name, login code, and phone number.")
    else:
        st.subheader("Teacher Master Login")
        passcode = st.text_input("Teacher Passcode", type="password")
        if st.button("Access Teacher Dashboard ➔"):
            if passcode == "admin123" or passcode == "":
                st.session_state.current_page = "teacher_dashboard"
                st.rerun()
            else:
                st.error("Incorrect passcode. Try admin123.")

# 2. STUDENT WINDOW SECURITY & PHONE CODE CHECKUP PAGE
elif st.session_state.current_page == "security_checkup":
    st.markdown("""
        <div class="header-card" style="background: linear-gradient(135deg, #744210 0%, #d69e2e 100%);">
            <h1>📱 Phone Code Verification</h1>
            <p>A secure 4-digit verification code has been sent to your mobile number.</p>
        </div>
    """, unsafe_allow_html=True)

    st.info(
        f"📲 **[SMS Gateway Simulator]** Code sent to **{st.session_state.phone}**. Your verification code is: **{st.session_state.otp_code}**")

    st.subheader("Enter Verification Code")
    entered_otp = st.text_input("4-Digit Code", max_chars=4, type="default")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Verify Code & Proceed ➔"):
            if entered_otp == st.session_state.otp_code:
                db["registered_students"][st.session_state.email] = {
                    "name": st.session_state.user,
                    "student_id": st.session_state.student_id,
                    "phone": st.session_state.phone,
                    "grade": st.session_state.grade,
                    "plan": st.session_state.plan or "Not Selected"
                }

                st.success(f"Code verified! Your Student ID is: **{st.session_state.student_id}**")

                if st.session_state.email in db["registered_students"]:
                    st.session_state.plan = db["registered_students"][st.session_state.email]["plan"]
                    st.session_state.current_page = "plans"
                else:
                    st.session_state.current_page = "plans"
                st.rerun()
            else:
                st.error("Invalid Code code. Please enter the correct code shown above.")
    with c2:
        if st.button("⬅ Back to Login"):
            st.session_state.current_page = "login"
            st.rerun()

# 3. PLAN SELECTION PAGE (STUDENT ONLY)
elif st.session_state.current_page == "plans":
    st.markdown("""
        <div class="header-card">
            <h1>Choose Your Learning Plan</h1>
            <p>Select the plan that fits your academic goals</p>
        </div>
    """, unsafe_allow_html=True)

    col_free, col_prem = st.columns(2)

    with col_free:
        with st.container(border=True):
            st.markdown("### 🆓 Free Plan")
            st.markdown("**Chapter Notes & Study Materials**")
            st.divider()
            st.markdown("✔️ PDF Study Materials")
            st.markdown("✔️ **Maths Quiz only**")
            st.markdown("❌ AI Companion")
            st.markdown("❌ General / All-Subject Quiz")
            st.write("")

            if st.button("Select Free Plan", key="btn_free"):
                st.session_state.plan = "Free"
                db["registered_students"][st.session_state.email] = {
                    "name": st.session_state.user,
                    "student_id": st.session_state.student_id,
                    "phone": st.session_state.phone,
                    "grade": st.session_state.grade,
                    "plan": "Free",
                    "excuse": ""
                }

                email_subject = f"New Free Plan Signup: {st.session_state.user}"
                email_html = f"""
                <html><body style="font-family: Arial, sans-serif;">
                <h2>Skill Nest - New Free Plan Signup</h2>
                <p>A student has selected the <b>Free Plan</b>.</p>
                <ul>
                    <li><b>Student ID:</b> {st.session_state.student_id}</li>
                    <li><b>Name:</b> {st.session_state.user}</li>
                    <li><b>Login Code/Email:</b> {st.session_state.email}</li>
                    <li><b>Phone:</b> {st.session_state.phone}</li>
                    <li><b>Grade:</b> {st.session_state.grade}</li>
                    <li><b>Plan:</b> Free</li>
                </ul>
                </body></html>
                """
                email_sent = send_html_email(
                    "mahith.balegar@gmail.com", email_subject, email_html
                )

                st.session_state.current_page = "dashboard"
                if email_sent:
                    st.success("Free Plan selected! Admin notification email sent.")
                else:
                    st.warning("Free Plan selected, but the admin email could not be sent.")
                st.rerun()

    with col_prem:
        with st.container(border=True):
            st.markdown("### 🏫 School Payment (Premium)")
            st.markdown("**Send a payment notification and optional excuse to the school**")
            st.divider()
            st.markdown("✔️ Live Timetable & Google Meet Classes")
            st.markdown("✔️ Chapter Notes & Study Materials")
            st.markdown("✔️ 🤖 **AI Companion**")
            st.markdown("✔️ Full Premium Learning Features")
            st.markdown("❌ No General / Normal Quiz")
            st.write("")

            # Optional excuse field inside premium plan
            school_excuse = st.text_area(
                "Optional Excuse / Reason (e.g. delay note):",
                placeholder="Optional: Enter any excuse or note here if needed...",
                key="premium_optional_excuse"
            )

            if st.button("🏫 Send Cash to School", key="btn_prem"):
                st.session_state.plan = "Premium"
                db["registered_students"][st.session_state.email] = {
                    "name": st.session_state.user,
                    "student_id": st.session_state.student_id,
                    "phone": st.session_state.phone,
                    "grade": st.session_state.grade,
                    "plan": "Premium",
                    "excuse": school_excuse.strip()
                }

                email_subject = f"Skill Nest - School Payment & Excuse: {st.session_state.user}"
                email_html = f"""
                <html><body style="font-family: Arial, sans-serif;">
                <h2>Skill Nest - School Payment Notification</h2>
                <p>A student has requested to send cash to the school under the <b>Premium Plan</b>.</p>
                <ul>
                    <li><b>Student ID:</b> {st.session_state.student_id}</li>
                    <li><b>Name:</b> {st.session_state.user}</li>
                    <li><b>Login Code/Email:</b> {st.session_state.email}</li>
                    <li><b>Phone:</b> {st.session_state.phone}</li>
                    <li><b>Grade:</b> {st.session_state.grade}</li>
                    <li><b>Request:</b> Send cash to school</li>
                    <li><b>Optional Excuse:</b> {school_excuse.strip() if school_excuse.strip() else 'None provided'}</li>
                </ul>
                </body></html>
                """
                email_sent = send_html_email(
                    "mahith.balegar@gmail.com", email_subject, email_html
                )

                st.session_state.current_page = "dashboard"
                if email_sent:
                    st.success("School payment notification & optional excuse sent successfully.")
                else:
                    st.warning("School payment processed, but the email notification could not be sent.")
                st.rerun()

    st.divider()
    if st.button("⬅ Back to Login"):
        st.session_state.current_page = "login"
        st.rerun()

# 4. TEACHER ADMINISTRATION DASHBOARD
elif st.session_state.current_page == "teacher_dashboard":
    st.markdown("""
        <div class="header-card">
            <h1>👨‍🏫 Skill Nest Teacher Administration Portal</h1>
            <p>Manage students, plans, timetable, student excuses, and quiz results.</p>
        </div>
    """, unsafe_allow_html=True)

    st.success("Teacher login successful.")

    st.subheader("👥 Registered Students & Student Excuses")
    if db.get("registered_students"):
        for email, student in db["registered_students"].items():
            with st.container(border=True):
                st.markdown(f"**{student.get('name', 'Student')}**")
                st.write(f"Student ID: {student.get('student_id', 'N/A')}")
                st.write(f"Login Code: {email}")
                st.write(f"Phone: {student.get('phone', 'N/A')}")
                st.write(f"Grade: {student.get('grade', 'N/A')}")
                st.write(f"Plan: **{student.get('plan', 'N/A')}**")

                # Display optional excuse if provided by student
                excuse_text = student.get('excuse', '').strip()
                if excuse_text:
                    st.info(f"💬 **Optional Excuse / Note:** {excuse_text}")
                else:
                    st.caption("💬 Optional Excuse: None provided")
    else:
        st.info("No registered students yet.")

    st.divider()

    st.subheader("🧠 Active Memory — Notes Awaiting Review")
    active_memory = db.get("active_memory_notes", [])
    pending_memory = [x for x in active_memory if x.get("status") == "Pending Teacher Review"]
    if pending_memory:
        for item in pending_memory:
            with st.container(border=True):
                st.markdown(f"### {item.get('name', 'Student')} — {item.get('id', 'N/A')}")
                st.write(f"Grade: {item.get('grade', 'N/A')} | Submitted: {item.get('submitted_at', 'N/A')}")
                if item.get("automatic"):
                    st.warning("⏱️ Automatically submitted after the 20-second Active Memory timer.")
                else:
                    st.info("📤 Submitted by the student.")
                st.markdown("**Student's Notes**")
                st.write(item.get("notes", ""))
                with st.expander("View the AI answer the student read"):
                    st.write(item.get("ai_answer", ""))
                st.markdown("**Teacher Review**")
                feedback = st.text_area("Feedback", key=f"am_feedback_{item['id']}", placeholder="Tell the student why the notes are correct or what needs fixing.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Notes Correct", key=f"am_correct_{item['id']}"):
                        item["status"] = "Correct"
                        item["teacher_feedback"] = feedback.strip() or "Your notes are correct. Good work!"
                        st.success("Marked Correct. The student will see the teacher feedback on their next Active Memory check.")
                        st.rerun()
                with c2:
                    if st.button("❌ Notes Need Correction", key=f"am_wrong_{item['id']}"):
                        item["status"] = "Needs Correction"
                        item["teacher_feedback"] = feedback.strip() or "Please review the lesson and improve your notes."
                        st.warning("Marked as Needs Correction.")
                        st.rerun()
    else:
        st.info("No Active Memory notes are waiting for teacher review.")

    st.divider()

    st.subheader("📊 Quiz Submissions")
    quiz_results = db.get("quiz_results", [])
    if quiz_results:
        for result in quiz_results:
            with st.container(border=True):
                st.write(f"**Student:** {result.get('name', 'N/A')}")
                st.write(
                    f"Grade: {result.get('grade', 'N/A')} | "
                    f"Subject: {result.get('subject', 'N/A')} | "
                    f"Score: {result.get('score', 'N/A')} / 20"
                )
    else:
        st.info("No quiz submissions yet.")

    st.divider()

    st.subheader("📅 Timetable / Publish Google Meet Slot")
    with st.form("slot_form"):
        slot_grade = st.selectbox(
            "Select Grade for Slot",
            ["Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10"]
        )
        slot_subject = st.selectbox(
            "Subject",
            ["Mathematics", "Science", "Social Studies (SST)", "English", "Telugu"]
        )
        slot_topic = st.text_input("Topic / Title", "Live Interactive Class")
        slot_date = st.text_input("Date", "2026-08-15")
        slot_time = st.text_input("Time", "10:00 AM")
        custom_meet_link = st.text_input("Google Meet Link", st.session_state.meet_link)

        publish_btn = st.form_submit_button("Publish Meet Slot & Notify Students")

    if publish_btn:
        st.session_state.meet_link = custom_meet_link
        db["active_slots"].append({
            "grade": slot_grade,
            "subject": slot_subject,
            "topic": slot_topic,
            "date": slot_date,
            "time": slot_time,
            "link": custom_meet_link
        })

        meet_email_sent = 0
        meet_email_failed = 0

        for student in db.get("registered_students", {}).values():
            if student.get("grade") == slot_grade and student.get("email"):
                meet_html = f"""
                <html><body style="font-family:Arial,sans-serif;">
                <h2>🎓 Skill Nest Live Class</h2>
                <p>Your teacher has scheduled a live Google Meet class.</p>
                <p><b>Subject:</b> {slot_subject}<br>
                <b>Topic:</b> {slot_topic}<br>
                <b>Date:</b> {slot_date}<br>
                <b>Time:</b> {slot_time}</p>
                <p><a href="{custom_meet_link}">Join Google Meet</a></p>
                </body></html>
                """
                if send_html_email(
                        student["email"],
                        f"Skill Nest Live Class - {slot_subject}",
                        meet_html
                ):
                    meet_email_sent += 1
                else:
                    meet_email_failed += 1

        st.success(
            f"Google Meet published for {slot_grade}. "
            f"Emails sent: {meet_email_sent}; failed: {meet_email_failed}."
        )

    st.warning("Deleting all Meet links removes them from the student view.")
    if st.button("🗑️ Delete All Google Meet Links", key="delete_all_meet_links"):
        db["active_slots"] = []
        st.success("All Google Meet links have been deleted. They are no longer visible to students.")
        st.rerun()

    st.divider()

    if st.button("⬅ Log out of Teacher Portal", key="teacher_logout"):
        st.session_state.current_page = "login"
        st.rerun()

# 5. STUDENT DASHBOARD & SEPARATE NAVIGATION PAGES
elif st.session_state.current_page == "dashboard":
    st.sidebar.title(f"👤 {st.session_state.user}")
    st.sidebar.write(f"Student ID: **{st.session_state.student_id}**")
    st.sidebar.write(f"Login Code: {st.session_state.email}")
    st.sidebar.write(f"Phone: {st.session_state.phone}")
    st.sidebar.write(f"Grade: {st.session_state.grade}")
    st.sidebar.write(f"Plan: **{st.session_state.plan} Plan**")
    st.sidebar.divider()

    # Premium students get AI Companion; Free students get Maths Quiz only.
    if st.session_state.plan == "Premium":
        student_nav = st.sidebar.radio("Navigate Sections:", [
            "📖 Handbooks & Chapters (Math / Science / SST / English / Telugu)",
            "📅 Live Timetable & Classes",
            "🤖 AI Companion"
        ])
    else:
        student_nav = st.sidebar.radio("Navigate Sections:", [
            "📖 Handbooks & Chapters (Math / Science / SST / English / Telugu)",
            "📅 Live Timetable & Classes",
            "🧮 Maths Quiz"
        ])

    st.sidebar.divider()
    if st.sidebar.button("⬅ Log out / Switch Account"):
        st.session_state.current_page = "login"
        st.rerun()

    # SECTION 1: HANDBOOKS & CHAPTERS WITH SUBJECT SELECTOR
    if student_nav == "📖 Handbooks & Chapters (Math / Science / SST / English / Telugu)":
        st.markdown(f"""
            <div class="header-card">
                <h1>Welcome, {st.session_state.user}</h1>
                <p>Student ID: <b>{st.session_state.student_id}</b> | Grade: <b>{st.session_state.grade}</b> | Plan: <b>{st.session_state.plan} Plan</b></p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader("📚 Select Subject to View Chapters")
        selected_subject = st.radio("Choose Subject:",
                                    ["Mathematics", "Science", "Social Studies (SST)", "English", "Telugu"],
                                    horizontal=True)

        if selected_subject == "Mathematics":
            chapters = MATH_SYLLABUS_DATABASE.get(st.session_state.grade, MATH_SYLLABUS_DATABASE["Grade 5"])
        elif selected_subject == "Science":
            chapters = SCIENCE_SYLLABUS_DATABASE.get(st.session_state.grade, SCIENCE_SYLLABUS_DATABASE["Grade 5"])
        elif selected_subject == "Social Studies (SST)":
            chapters = SST_SYLLABUS_DATABASE.get(st.session_state.grade, SST_SYLLABUS_DATABASE["Grade 5"])
        elif selected_subject == "English":
            chapters = ENGLISH_SYLLABUS_DATABASE.get(st.session_state.grade, ENGLISH_SYLLABUS_DATABASE["Grade 5"])
        else:
            chapters = TELUGU_SYLLABUS_DATABASE.get(st.session_state.grade, TELUGU_SYLLABUS_DATABASE["Grade 5"])

        st.divider()
        st.info("📚 Study the chapter notes below.")
        st.divider()
        st.markdown(f"## 📖 {selected_subject} Chapters ({st.session_state.grade}) — Full Notes")
        for ch in chapters:
            with st.expander(ch["ch"]):
                st.write(ch["notes"])

    # SECTION 2: LIVE GOOGLE MEET CLASSES & TIMETABLE
    elif student_nav == "📅 Live Timetable & Classes":
        st.markdown(f"""
            <div class="header-card">
                <h1>📅 Live Timetable & Google Meet Classes</h1>
                <p>Viewing scheduled sessions for your class: <b>{st.session_state.grade}</b>. Published meeting slots and join buttons appear below.</p>
            </div>
        """, unsafe_allow_html=True)

        grade_slots = [s for s in db["active_slots"] if s['grade'] == st.session_state.grade]

        if not grade_slots:
            st.info(f"No active live timetable slots published for **{st.session_state.grade}** yet. Check back soon!")
        else:
            st.success(f"🔔 **Active Live Sessions for {st.session_state.grade}:**")
            for slot in grade_slots:
                st.markdown(f"""
                    <div class="meet-card">
                        <h3 style="color: #1a365d; margin-top: 0;">📚 Subject: {slot['subject']}</h3>
                        <p style="font-size: 16px; margin: 5px 0;"><b>Meeting Title / Topic:</b> {slot['topic']}</p>
                        <p style="font-size: 15px; margin: 5px 0; color: #2d3748;"><b>🗓 Date:</b> {slot['date']} &nbsp;|&nbsp; <b>⏰ Time:</b> {slot['time']}</p>
                        <div style="margin-top: 15px;">
                            <a href="{slot['link']}" target="_blank" style="background: linear-gradient(135deg, #2b6cb0 0%, #1a365d 100%); color: white; padding: 10px 22px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">🎥 Join Google Meet Now</a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    # SECTION 3: AI COMPANION + ACTIVE MEMORY (PREMIUM ONLY)
    elif student_nav == "🤖 AI Companion":
        st.markdown(f"""
            <div class="header-card">
                <h1>🤖 AI Companion</h1>
                <p>Your Premium study companion for {st.session_state.grade}.</p>
            </div>
        """, unsafe_allow_html=True)

        if not st.session_state.ai_answer or not st.session_state.ai_reading_complete:
            st.info("Ask questions about your lessons. After reading the answer, click **Reading Over** to enter Active Memory Notes.")

        if not st.session_state.ai_reading_complete:
            ai_question = st.text_area(
                "What do you want to learn?",
                value=st.session_state.ai_question,
                placeholder="Example: Explain pressure in simple words with an example.",
                key="ai_question_box"
            )

            if st.button("✨ Ask AI Companion", key="ask_ai_companion"):
                if not ai_question.strip():
                    st.warning("Please type a question first.")
                else:
                    api_key = MISTRAL_API_KEY.strip()
                    if not api_key or api_key == "PASTE_YOUR_NEW_MISTRAL_API_KEY_HERE":
                        st.error("MISTRAL_API_KEY is not configured. Put your new Mistral API key at the top of this file in MISTRAL_API_KEY.")
                    else:
                        with st.spinner("AI Companion is thinking..."):
                            try:
                                prompt = (
                                    f"You are a friendly educational AI companion for a {st.session_state.grade} student. "
                                    f"Explain concepts clearly, step-by-step, using simple school-level language. "
                                    f"Give examples when useful. Do not unnecessarily use advanced terminology.\n\n"
                                    f"Student question: {ai_question.strip()}"
                                )
                                payload = json.dumps({
                                    "model": "mistral-small-latest",
                                    "messages": [
                                        {"role": "system", "content": "You are a helpful school-level educational tutor."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    "temperature": 0.3,
                                    "max_tokens": 1200
                                }).encode("utf-8")
                                request = urllib.request.Request(
                                    "https://api.mistral.ai/v1/chat/completions",
                                    data=payload,
                                    headers={
                                        "Authorization": f"Bearer {api_key}",
                                        "Content-Type": "application/json",
                                        "Accept": "application/json",
                                    },
                                    method="POST",
                                )
                                with urllib.request.urlopen(request, timeout=45) as response:
                                    result = json.loads(response.read().decode("utf-8"))
                                st.session_state.ai_question = ai_question.strip()
                                st.session_state.ai_answer = result["choices"][0]["message"]["content"]
                                st.session_state.ai_reading_complete = False
                                st.rerun()
                            except urllib.error.HTTPError as e:
                                details = e.read().decode("utf-8", errors="replace")
                                st.error(f"Mistral API error ({e.code}): {details}")
                            except urllib.error.URLError as e:
                                st.error(f"Network error while contacting Mistral: {e.reason}")
                            except (KeyError, IndexError, TypeError) as e:
                                st.error(f"Unexpected Mistral response: {type(e).__name__}: {e}")
                            except Exception as e:
                                st.error(f"AI Companion error: {type(e).__name__}: {e}")

            if st.session_state.ai_answer:
                st.markdown("### 💡 AI Companion")
                st.write(st.session_state.ai_answer)
                st.divider()
                if st.button("📖 Reading Over — Open Active Memory Notes", key="reading_over"):
                    st.session_state.ai_reading_complete = True
                    st.session_state.active_memory_started_at = time.time()
                    st.session_state.active_memory_notes = ""
                    st.rerun()

        else:
            # The AI chat answer disappears once Reading Over is clicked.
            elapsed = time.time() - (st.session_state.active_memory_started_at or time.time())
            remaining = max(0, 20 - int(elapsed))

            st.markdown("### 📝 Active Memory Notes")
            st.success("The AI answer is now hidden. Write everything you remember in your own words.")
            st.caption("⏱️ Send your notes to the teacher within 20 seconds. If you do nothing, Skill Nest will submit them automatically.")

            st.text_area(
                "Write your notes here",
                value=st.session_state.active_memory_notes,
                key="active_memory_notes_box",
                height=260,
                placeholder="Write the important points you remember from the AI explanation..."
            )

            c1, c2 = st.columns([2, 1])
            with c1:
                if st.button("📤 Send Notes to Teacher", key="send_active_memory"):
                    st.session_state.active_memory_notes = st.session_state.active_memory_notes_box
                    submit_active_memory_notes(st.session_state.active_memory_notes, automatic=False)
                    st.success("Your Active Memory notes were sent to the teacher for review.")
                    st.rerun()
            with c2:
                st.metric("Auto-send in", f"{remaining}s")

            if elapsed >= 20:
                st.session_state.active_memory_notes = st.session_state.active_memory_notes_box
                submit_active_memory_notes(st.session_state.active_memory_notes, automatic=True)
                st.warning("⏱️ 20 seconds passed. Your notes were automatically sent to the teacher.")
                st.rerun()
            else:
                # Browser refresh makes the 20-second auto-submit reliable even when the student does nothing.
                st.markdown(
                    f"""<script>setTimeout(function() {{ window.parent.location.reload(); }}, {(remaining + 1) * 1000});</script>""",
                    unsafe_allow_html=True
                )

            st.divider()
            st.subheader("👨‍🏫 Teacher Review")
            my_notes = [x for x in db.get("active_memory_notes", []) if x.get("student_id") == st.session_state.student_id]
            if my_notes:
                latest = my_notes[-1]
                if latest.get("status") == "Correct":
                    st.success("✅ Teacher says your notes are correct!")
                    if latest.get("teacher_feedback"):
                        st.info(f"Teacher feedback: {latest['teacher_feedback']}")
                elif latest.get("status") == "Needs Correction":
                    st.error("❌ Teacher says your notes need correction.")
                    if latest.get("teacher_feedback"):
                        st.warning(f"Teacher feedback: {latest['teacher_feedback']}")
                else:
                    st.info("⏳ Your notes are waiting for the teacher to review them.")
            else:
                st.info("No Active Memory submission yet.")

    # SECTION 4: MATHS QUIZ (FREE PLAN ONLY)
    elif student_nav == "🧮 Maths Quiz":
        st.markdown(f"""
            <div class="header-card">
                <h1>🧮 Maths Quiz ({st.session_state.grade})</h1>
                <p>Free-plan maths quiz with instant scoring sent to your teacher.</p>
            </div>
        """, unsafe_allow_html=True)

        quiz_subject = "Mathematics"
        sub_chapters = MATH_SYLLABUS_DATABASE.get(
            st.session_state.grade, MATH_SYLLABUS_DATABASE["Grade 5"]
        )

        quiz_chapter = st.selectbox("Select Chapter for Exam", [c["ch"] for c in sub_chapters])
        quiz_difficulty = st.selectbox("Select Test Difficulty Tier", ["Easy", "Medium", "Hard", "Expert"])

        st.markdown("### 🔑 Student Verification")
        entered_test_id = st.text_input("Enter Your Student ID (e.g., Name123):", value=st.session_state.student_id)

        if st.button("🚀 Start Quiz"):
            if entered_test_id.strip() == "":
                st.error("Please enter a valid Student ID.")
            else:
                st.session_state.active_quiz = generate_20_questions(st.session_state.grade, quiz_chapter, quiz_subject,
                                                                     quiz_difficulty)
                st.success(
                    f"Generated 20 questions for Student ID **{entered_test_id}** on [{quiz_subject}] {quiz_chapter} ({quiz_difficulty} level)!")

        if "active_quiz" in st.session_state and st.session_state.active_quiz:
            st.markdown(f"### 📋 Active Test: [{quiz_subject}] {quiz_chapter} ({quiz_difficulty})")
            with st.form("exam_form"):
                user_answers = []
                for idx, q in enumerate(st.session_state.active_quiz):
                    st.markdown(f"**{q['question']}**")
                    ans = st.radio(f"Select option for Q{idx + 1}", q["options"], key=f"q_num_{idx}")
                    user_answers.append(ans)
                    st.write("")

                submitted_exam = st.form_submit_button("Submit Exam & Send to Teacher")
                if submitted_exam:
                    if entered_test_id.strip() == "":
                        st.error("Student ID cannot be blank to submit exam.")
                    else:
                        score = sum(
                            1 for idx, q in enumerate(st.session_state.active_quiz) if user_answers[idx] == q["answer"])
                        percentage = (score / 20) * 100

                        db["quiz_results"].append({
                            "name": st.session_state.user,
                            "student_id": entered_test_id.strip(),
                            "grade": st.session_state.grade,
                            "subject": quiz_subject,
                            "chapter": quiz_chapter,
                            "difficulty": quiz_difficulty,
                            "score": score,
                            "percentage": percentage
                        })

                        exam_email_subject = f"Test Submission: {st.session_state.user} (ID: {entered_test_id.strip()})"
                        exam_email_html = f"""
                        <html>
                          <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                            <h2 style="color: #1a365d;">📝 Skill Nest Student Test Submission</h2>
                            <p>A student has completed and submitted an assessment:</p>
                            <ul>
                              <li><b>Student Name:</b> {st.session_state.user}</li>
                              <li><b>Student ID:</b> {entered_test_id.strip()}</li>
                              <li><b>Grade:</b> {st.session_state.grade}</li>
                              <li><b>Subject:</b> {quiz_subject}</li>
                              <li><b>Chapter:</b> {quiz_chapter}</li>
                              <li><b>Difficulty:</b> {quiz_difficulty}</li>
                              <li><b>Score:</b> {score} / 20 ({percentage}%)</li>
                            </ul>
                            <p style="margin-top: 20px; color: #718096; font-size: 12px;">Skill Nest Portal - AP State Syllabus</p>
                          </body>
                        </html>
                        """
                        quiz_email_sent = send_html_email(
                            st.session_state.teacher_email,
                            exam_email_subject,
                            exam_email_html
                        )

                        st.success(f"Exam submitted! Score: {score} / 20 ({percentage}%).")
                        if quiz_email_sent:
                            st.info("The teacher was notified by email.")
                        else:
                            st.warning("The score was saved, but the teacher email was not sent.")
                        if score >= 16:
                            st.balloons()
