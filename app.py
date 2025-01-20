import os
import streamlit as st
from PIL import Image
from utils.utils import generate_answer, generate_base_prompt, get_azure_client, generate_explanation, test_regex, markdown_test_results
from streamlit_extras.colored_header import colored_header

# Set OpenAI API key
#os.environ["OPENAI_API_KEY"] = st.secrets["AZURE"]["AZURE_OPENAI_API_KEY"]

# Create directory if it doesn't exist
#data = "data"
#os.makedirs(data, exist_ok=True)

# Setup Streamlit page config
st.set_page_config(
    page_title="REGEX-GENERATOR",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon="./logo/sparkle-orange-icon.png"
)

# Load and display the logo
image = Image.open("./logo/sparkle-orange-icon.png")
#st.image(image, width=100)

# App title and introduction

col_logo, col_title = st.columns([0.1, 0.9])
with col_logo:
    st.image(image, width=80)
with col_title:
    st.title(":gray[RegEx Generator]")
#st.markdown("*Generate regular expressions effortlessly via the Regex Generator in natural language*")

# Custom function to style the app
def style_app():
    st.markdown("""
    <style>
    .app-header { visibility: hidden; }
    .css-18e3th9 { padding-top: 0; padding-bottom: 0; }
    .css-1d391kg { padding-top: 1px; padding-right: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)


# Initialize Azure OpenAI client
azure_client = get_azure_client()


# Add these functions at the top level, before main()
def init_session_state():
    if 'pattern_examples' not in st.session_state:
        st.session_state.pattern_examples = [('', '')]
    if 'pattern_not_examples' not in st.session_state:
        st.session_state.pattern_not_examples = [('', '')]
    if 'pattern_example_sentences' not in st.session_state:
        st.session_state.pattern_example_sentences = ''


def add_input_field(field_type):
    st.session_state[field_type].append(('', ''))  # Append tuple of empty strings


def remove_input_field(field_type, index):
    st.session_state[field_type].pop(index)


def create_input_section(title, field_type, icon):
    examples = []
    descriptions = []
    for i, (example, description) in enumerate(st.session_state[field_type]):
        col1, col2, col3 = st.columns([2, 6, 0.3])
        with col1:
            example = st.text_input(
                f"{icon} Example {i + 1}" if i > 0 else f"{icon}",
                value=example,
                key=f"{field_type}_example_{i}"
            )
            examples.append(example)
        with col2:
            description = st.text_input(
                f"Description {i+1}" if i > 0 else "Description",
                value=description,
                key=f"{field_type}_description_{i}"
            )
            
            descriptions.append(description)
        with col3:
            if i > 0:  # Only show remove button for additional fields
                st.button("🗑️", key=f"del_{field_type}_{i}", 
                         on_click=remove_input_field,
                         args=(field_type, i))
    
    st.button("Add", key=f"add_{field_type}",
              on_click=add_input_field,
              args=(field_type,))
    
    return zip(examples, descriptions)


def main():
    # Initialize session state variables
    init_session_state()
    if 'result_regex' not in st.session_state:
        st.session_state.result_regex = None
    if 'test_text' not in st.session_state:
        st.session_state.test_text = ''
    if 'show_test_results' not in st.session_state:
        st.session_state.show_test_results = False


    #input_col, _, output_col = st.columns([1, 0.05, 1])
    #input_col = st.columns(1)
    

    #with input_col:
    with st.container(border=True, height=500):
        colored_header(
                label="Create a Regular Expression",
                description="",
                color_name="blue-70")
        
        # Input field for user to enter the pattern
        pattern_description = st.text_input("Describe in detail what you want the regex pattern to match:",
                                            placeholder="Eg. match email addresses starting with a capital, and are not at the start of a sentence")
        
        # Replace the single input fields with our new multi-input sections
        pattern_examples = create_input_section(
            "Enter an example of a word that you want the pattern to match:",
            'pattern_examples',
            "✔️ Match Example"
        )
        st.divider()
        
        pattern_not_examples = create_input_section(
            "Enter an example of a word that you don't want the pattern to match:",
            'pattern_not_examples',
            "❌ Not Match Example"
        )
        st.divider()

        #pattern_example_sentences = create_input_section(
        #    "Enter an example sentence that contains both the pattern you want to match and the pattern you don't want to match:",
        #    'pattern_example_sentences',
        #    "🔍 Example Sentence"
        #) 

        pattern_example_sentences = st.text_input("Enter an example sentence that contains both the pattern you want to match and the pattern you don't want to match:",
                                                value=st.session_state.pattern_example_sentences)
        # Update the generate button logic to use all examples
        if st.button("Generate Regular Expression", type="primary"):
            #print(pattern_examples)
            base_prompt = generate_base_prompt(
                pattern_description,
                pattern_examples,
                pattern_not_examples,
                pattern_example_sentences
            )
            #print(base_prompt)
            st.session_state.result_regex = generate_answer(base_prompt, azure_client)
            st.session_state.explanation = generate_explanation(base_prompt, st.session_state.result_regex, azure_client)
            st.session_state.show_test_results = False

    output_col, _, test_col = st.columns([1, 0.05, 1])
    with output_col:
        with st.container(border=True, height=500):
            colored_header(
                    label="Results",
                    description="",
                    color_name="red-70")
            
            # Display results if we have a regex
            if st.session_state.result_regex:
                st.subheader("Generated Regular Expression")
                st.code(f"\n{st.session_state.result_regex}\n", language="regex")

        
                st.subheader("Explanation")
                st.write(st.session_state.explanation)
        
    with test_col:
        with st.container(border=True, height=500):
            colored_header(
                label="Test the Result",
                description="",
                color_name="violet-70")
            
            st.session_state.test_text = st.text_input("Enter an example sentence to test the regex", 
                                                        value=st.session_state.test_text)
            
            if st.button("Run Test", type="primary"):
                st.session_state.show_test_results = True
            
            # Show test results if button was clicked
            if st.session_state.show_test_results and st.session_state.test_text:
                markdown_result = markdown_test_results(
                    test_regex(st.session_state.result_regex, st.session_state.test_text)
                )
                st.markdown(markdown_result)


# Run the app
if __name__ == "__main__":
    main()

    #with st.expander("ℹ️ - About this App"):
     #   st.markdown("""This app harnesses the Azure OpenAI module to streamline regular expression generation, simplifying intricate pattern queries into intuitive prompts for seamless data analysis.""")