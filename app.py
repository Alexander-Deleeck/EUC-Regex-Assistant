import os
import streamlit as st
from PIL import Image
import clipboard
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
    layout="centered",
    initial_sidebar_state="auto",
    page_icon="./logo/sparkle-orange-icon.png"
)

# Load and display the logo
image = Image.open("./logo/sparkle-orange-icon.png")
st.image(image, width=100)

# App title and introduction
st.title("Regex Generator💡")
st.markdown("Generate regular expressions effortlessly with this Regex Generator, simplifying complex pattern queries.")

# Custom function to style the app
def style_app():
    st.markdown("""
    <style>
    .app-header { visibility: hidden; }
    .css-18e3th9 { padding-top: 0; padding-bottom: 0; }
    .css-1d391kg { padding-top: 1rem; padding-right: 1rem; padding-bottom: 1rem; padding-left: 1rem; }
    </style>
    """, unsafe_allow_html=True)


# Initialize Azure OpenAI client
azure_client = get_azure_client()


# Define the Streamlit app
def copy_to_clipboard(text):
    clipboard.copy(text)
    st.toast(f"Copied to clipboard: {text}", icon='✅')


def main():
    # Initialize session state variables if they don't exist
    if 'result_regex' not in st.session_state:
        st.session_state.result_regex = None
    if 'test_text' not in st.session_state:
        st.session_state.test_text = ''
    if 'show_test_results' not in st.session_state:
        st.session_state.show_test_results = False

    # Input field for user to enter the pattern
    pattern_description = st.text_input("Please describe in detail what you want the regex pattern to match:")
    pattern_examples = st.text_input("Enter an example of a word that you want the pattern to match:")
    pattern_not_examples = st.text_input("Enter an example of a word that you don't want the pattern to match:")
    pattern_example_sentence = st.text_input("Enter an example sentence that contains both the pattern you want to match and the pattern you don't want to match:")

    st.code(r'(?<![.!?]\s)(?<!^)\b[A-Z][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')

    if st.button("Generate Regular Expression"):
        # Generate regular expression using Azure OpenAI
        base_prompt = generate_base_prompt(pattern_description, pattern_examples, pattern_not_examples, pattern_example_sentence)
        st.session_state.result_regex = generate_answer(base_prompt, azure_client)
        st.session_state.explanation = generate_explanation(base_prompt, st.session_state.result_regex, azure_client)
        st.session_state.show_test_results = False  # Reset test results when generating new regex


    # Display results if we have a regex
    if st.session_state.result_regex:
        colored_header(
            label="Generated Regular Expression",
            description="This is the generated regular expression",
            color_name="red-70")
        st.code(f"```\n{st.session_state.result_regex}\n```")

        colored_header(
            label="Explanation",
            description="This is the explanation of the regular expression",
            color_name="violet-70")
        st.write(st.session_state.explanation)
        
        colored_header(
            label="Test the Result",
            description="This is the test results of the regular expression",
            color_name="violet-70")
        
        st.session_state.test_text = st.text_input("Enter an example sentence to test the regex", 
                                                  value=st.session_state.test_text)
        
        if st.button("Run Test"):
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

    with st.expander("ℹ️ - About this App"):
        st.markdown("""This app harnesses the Azure OpenAI module to streamline regular expression generation, simplifying intricate pattern queries into intuitive prompts for seamless data analysis.""")