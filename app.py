import streamlit as st
from PIL import Image
from utils.utils import (
    generate_answer, generate_base_prompt, get_azure_client, generate_explanation,
    test_regex, substitute_regex, markdown_test_results, read_file_content,
    test_regex_on_file, substitute_regex_in_file
)
from streamlit_extras.colored_header import colored_header

# Setup Streamlit page config
st.set_page_config(
    page_title="REGEX-GENERATOR",
    layout="wide",
    initial_sidebar_state="auto",
    page_icon="./logo/sparkle-orange-icon.png"
)

# Initialize Azure OpenAI client
azure_client = get_azure_client()

def init_session_state():
    if 'pattern_examples' not in st.session_state:
        st.session_state.pattern_examples = [('', '')]
    if 'pattern_not_examples' not in st.session_state:
        st.session_state.pattern_not_examples = [('', '')]
    if 'pattern_example_sentences' not in st.session_state:
        st.session_state.pattern_example_sentences = ''
    if 'find_regex' not in st.session_state:
        st.session_state.find_regex = ''
    if 'replace_regex' not in st.session_state:
        st.session_state.replace_regex = ''

def add_input_field(field_key):
    st.session_state[field_key].append(('', ''))

def remove_input_field(field_key, index):
    st.session_state[field_key].pop(index)

def create_input_section(field_key, label, icon):
    """
    Creates a section for input examples.
    
    Parameters:
      - field_key: the key in st.session_state (e.g., 'pattern_examples')
      - label: descriptive label for the examples (e.g., "Match Example")
      - icon: an icon to display alongside the label
    """
    examples = []
    descriptions = []
    for i, (example, description) in enumerate(st.session_state[field_key]):
        col1, col2, col3 = st.columns([2, 6, 0.3])
        with col1:
            example = st.text_input(
                f"{icon} {label} {i + 1}" if i > 0 else f"{icon} {label}",
                value=example,
                key=f"{field_key}_example_{i}"
            )
            examples.append(example)
        with col2:
            description = st.text_input(
                f"Description {i+1}" if i > 0 else "Description",
                value=description,
                key=f"{field_key}_description_{i}"
            )
            descriptions.append(description)
        with col3:
            if i > 0:
                st.button("🗑️", key=f"del_{field_key}_{i}", 
                          on_click=remove_input_field,
                          args=(field_key, i))
    
    st.button("Add", key=f"add_{field_key}",
              on_click=add_input_field,
              args=(field_key,))
    
    return list(zip(examples, descriptions))

def main():
    init_session_state()
    st.title(":blue[RegEx Generator]")

    with st.container():
        colored_header(label="Create a Regular Expression", color_name="blue-70")
        
        # Pattern description
        pattern_description = st.text_input(
            "Describe what to find and replace:",
            placeholder="Eg. Replace 'one' with '1' followed by non-breaking space"
        )
        
        # Examples sections (note: now the first parameter is the session state key)
        pattern_examples = create_input_section('pattern_examples', "Match Example", "✔️")
        st.divider()
        pattern_not_examples = create_input_section('pattern_not_examples', "Not Match Example", "❌")
        st.divider()
        
        # Example sentence
        pattern_example_sentences = st.text_input(
            "Example sentence containing matches and non-matches:",
            value=st.session_state.pattern_example_sentences
        )
        
        # Regex options
        col1, col2 = st.columns(2)
        with col1:
            prefix = st.text_input("Prefix (regex)")
        with col2:
            suffix = st.text_input("Suffix (regex)")
        
        case_sensitive = st.checkbox("Case-sensitive")
        start_para = st.checkbox("Find at start of paragraph")
        end_para = st.checkbox("Find at end of paragraph")

        if st.button("Generate Regular Expression", type="primary"):
            base_prompt = generate_base_prompt(
                pattern_description,
                pattern_examples,
                pattern_not_examples,
                pattern_example_sentences,
                prefix,
                suffix,
                case_sensitive,
                start_para,
                end_para
            )
            ai_response = generate_answer(base_prompt, azure_client)
            if '|||' in ai_response:
                find_part, replace_part = ai_response.split('|||', 1)
            else:
                find_part, replace_part = ai_response, ''
            
            st.session_state.find_regex = find_part.strip()
            st.session_state.replace_regex = replace_part.strip()
            st.session_state.explanation = generate_explanation(base_prompt, ai_response, azure_client)
            st.session_state.show_test_results = False

    # Results and Testing columns
    col_results, col_test = st.columns(2)
    
    with col_results:
        with st.container():
            colored_header(label="Results", color_name="red-70")
            if st.session_state.find_regex:
                st.subheader("Find Pattern")
                edited_find = st.text_input(
                    "Edit find pattern", 
                    value=st.session_state.find_regex
                )
                st.code(edited_find, language='regex')
                
                st.subheader("Replace Pattern")
                edited_replace = st.text_input(
                    "Edit replace pattern", 
                    value=st.session_state.replace_regex
                )
                st.code(edited_replace, language='text')
                
                st.session_state.edited_find = edited_find
                st.session_state.edited_replace = edited_replace
                
                st.subheader("Explanation")
                st.write(st.session_state.explanation)

    with col_test:
        with st.container():
            colored_header(label="Test", color_name="violet-70")
            test_tabs = st.tabs(["Text Test", "File Test"])
            
            with test_tabs[0]:
                test_text = st.text_area("Test text", height=100)
                if st.button("Test on Text"):
                    find = st.session_state.get('edited_find', st.session_state.find_regex)
                    replace = st.session_state.get('edited_replace', st.session_state.replace_regex)
                    
                    if find and test_text:
                        matches = test_regex(find, test_text)
                        substituted = substitute_regex(find, replace, test_text)
                        
                        st.subheader("Matches")
                        st.markdown(markdown_test_results(matches))
                        
                        st.subheader("Substituted Text")
                        st.code(substituted)
            
            with test_tabs[1]:
                uploaded_file = st.file_uploader("Upload .txt or .docx", type=["txt", "docx"])
                if uploaded_file and st.session_state.find_regex:
                    content = read_file_content(uploaded_file)
                    find = st.session_state.get('edited_find', st.session_state.find_regex)
                    replace = st.session_state.get('edited_replace', st.session_state.replace_regex)
                    
                    substituted = substitute_regex_in_file(find, replace, content)
                    matches = test_regex_on_file(find, content)
                    
                    st.subheader("Matches Found")
                    if matches:
                        for match in matches:
                            with st.expander(f"Match {match['match']}"):
                                st.write(match['context'])
                    else:
                        st.write("No matches found")
                    
                    st.download_button(
                        "Download Substituted File",
                        substituted.encode('utf-8'),
                        f"substituted_{uploaded_file.name}",
                        "text/plain"
                    )

if __name__ == "__main__":
    main()
