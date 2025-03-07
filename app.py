import streamlit as st
from utils.utils import (
    generate_answer, generate_base_prompt, get_azure_client, generate_explanation,
    test_regex, substitute_regex, markdown_test_results, read_file_content,
    test_regex_on_file, substitute_regex_in_file, generate_refinement_prompt, parse_refinement_response,
    check_auth
)
from streamlit_extras.colored_header import colored_header
import streamlit_shadcn_ui as ui
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
    if 'find_regex' not in st.session_state:
        st.session_state.find_regex = ''
    if 'replace_regex' not in st.session_state:
        st.session_state.replace_regex = ''
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'base_prompt' not in st.session_state:
        st.session_state.base_prompt = ''

def add_input_field(field_key):
    st.session_state[field_key].append(('', ''))

def remove_input_field(field_key, index):
    st.session_state[field_key].pop(index)

def create_input_section(field_key, label, icon):
    """Creates a section for input examples."""
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

def render_refinement_section():
    """Render the regex refinement chat interface"""
    with st.expander("🔧 Refine Regex with Follow-up Questions", expanded=False):
        if not st.session_state.get('find_regex'):
            st.info("Generate a regex first to enable refinement features.")
            return

        st.markdown("### Chat with the Regex Assistant")
        st.caption("Describe which test cases failed or what needs improvement")

        # Display chat history
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Assistant:**")
                st.code(f"New find pattern: {st.session_state.find_regex}\nNew replace pattern: {st.session_state.replace_regex}", 
                      language='regex')

        # Chat input
        user_input = st.text_input(
            "Your message:", 
            key="followup_input",
            placeholder="Eg. The pattern fails to match numbers followed by commas..."
        )
        
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button("Send", use_container_width=True):
                handle_refinement_input(user_input)
                #user_input.clear()
        with col2:
            st.button("Clear History", use_container_width=True,
                    help="Clear chat history and start over",
                    on_click=lambda: st.session_state.chat_history.clear())


def handle_refinement_input(user_input: str):
    """Process user refinement input and generate new regex"""
    if not user_input.strip():
        return

    # Add user message to history
    st.session_state.chat_history.append({'role': 'user', 'content': user_input.strip()})

    try:
        # Prepare messages for refinement
        messages = generate_refinement_prompt(
            st.session_state.base_prompt,
            st.session_state.find_regex,
            st.session_state.replace_regex,
            user_input.strip()
        )
        
        # Get LLM response
        response = azure_client.chat.completions.create(
            model=st.secrets["AZURE"]["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=messages,
            temperature=0.3
        )
        ai_response = response.choices[0].message.content
        
        # Parse and update regex
        new_find, new_replace = parse_refinement_response(ai_response)
        st.session_state.find_regex = new_find
        st.session_state.replace_regex = new_replace
        
        # Update explanation
        new_ai_response = f"{new_find}|||{new_replace}"
        st.session_state.explanation = generate_explanation(
            st.session_state.base_prompt,
            new_ai_response,
            azure_client
        )
        
        # Add assistant response to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': f"Updated pattern based on your feedback"
        })
        
        st.rerun()
    except Exception as e:
        st.error(f"Error generating refinement: {str(e)}")

def main():
    init_session_state()
    st.title(":blue[RegEx Generator]")
    
    # Add logout button to sidebar
    with st.sidebar:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
    with st.container():
        colored_header(label="Create a Regular Expression", color_name="blue-70", description=' ')
        
        # Pattern description and input sections
        pattern_description = st.text_input(
            "Describe what to find and replace:",
            placeholder="Eg. Replace 'one' with '1' followed by non-breaking space"
        )
        pattern_examples = create_input_section('pattern_examples', "Match Example", "✔️")
        st.divider()
        pattern_not_examples = create_input_section('pattern_not_examples', "Not Match Example", "❌")
        st.divider()
        
        # Regex options
        col1, col2 = st.columns(2)
        with col1: prefix = st.text_input("Prefix (regex)")
        with col2: suffix = st.text_input("Suffix (regex)")
        case_sensitive = ui.switch(default_checked=False, label="Case-sensitive", key="switch1")
        start_para = ui.switch(default_checked=False, label="Find at start of paragraph", key="switch2")
        end_para = ui.switch(default_checked=False, label="Find at end of paragraph", key="switch3")

        if st.button("Generate Regular Expression", type="primary"):
            base_prompt = generate_base_prompt(
                pattern_description,
                pattern_examples,
                pattern_not_examples,
                prefix,
                suffix,
                case_sensitive,
                start_para,
                end_para
            )
            st.session_state.base_prompt = base_prompt
            ai_response = generate_answer(base_prompt, azure_client)
            find_part, replace_part = ai_response.split('|||', 1) if '|||' in ai_response else (ai_response, '')
            
            st.session_state.find_regex = find_part.strip()
            st.session_state.replace_regex = replace_part.strip()
            st.session_state.explanation = generate_explanation(base_prompt, ai_response, azure_client)
            st.session_state.chat_history = []  # Reset chat history on new generation

    # Results and Testing columns
    col_results, col_test = st.columns(2)
    
    with col_results:
        with st.container():
            colored_header(label="Results", color_name="red-70", description=' ')
            if st.session_state.find_regex:
                st.subheader("Find Pattern")
                edited_find = st.text_input("Edit find pattern", value=st.session_state.find_regex)
                st.code(edited_find, language='regex')
                
                st.subheader("Replace Pattern")
                edited_replace = st.text_input("Edit replace pattern", value=st.session_state.replace_regex)
                st.code(edited_replace, language='text')
                
                st.session_state.edited_find = edited_find
                st.session_state.edited_replace = edited_replace
                
                st.subheader("Explanation")
                st.write(st.session_state.explanation)

    with col_test:
        with st.container():
            colored_header(label="Test", color_name="violet-70", description=' ')
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

    # Add refinement section
    render_refinement_section()

if __name__ == "__main__":
    check_auth()  # Add this before main()
    main()