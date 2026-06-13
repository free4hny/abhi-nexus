content = open('/app/streamlit_app.py').read()

start = content.find('def narration_buttons(article: dict):')
end   = content.find('\ndef article_card', start)

print("start:", start, "end:", end)

if start == -1 or end == -1:
    print("ERROR: Could not find function boundaries")
    exit()

new_func = '''def narration_buttons(article: dict):
    en_text = (article.get("ai_summary") or
               article.get("summary") or
               article.get("title") or "")[:800]
    hi_text = (article.get("hindi_summary") or en_text)[:800]
    col1, col2 = st.columns(2)
    with col1:
        if st.button("EN", key=f"en_{article.get('id','')}_btn",
                     use_container_width=True):
            with st.spinner("Generating..."):
                try:
                    r = requests.post(
                        f"{API_URL}/tts",
                        headers=headers(),
                        json={"text": en_text, "lang": "en"},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        st.audio(r.content, format="audio/mp3")
                    else:
                        st.error("Failed")
                except Exception as e:
                    st.error(str(e))
    with col2:
        if st.button("Hindi", key=f"hi_{article.get('id','')}_btn",
                     use_container_width=True):
            with st.spinner("Generating..."):
                try:
                    r = requests.post(
                        f"{API_URL}/tts",
                        headers=headers(),
                        json={"text": hi_text, "lang": "hi"},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        st.audio(r.content, format="audio/mp3")
                    else:
                        st.error("Failed")
                except Exception as e:
                    st.error(str(e))

'''

content = content[:start] + new_func + content[end:]
open('/app/streamlit_app.py', 'w').write(content)
print("Done")
