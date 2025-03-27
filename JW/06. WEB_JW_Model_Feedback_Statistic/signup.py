import streamlit as st

class Signup_page():
    def __init__(self):
        pass

    def run(self):
        st.header("📝 회원가입")
        
        # 회원가입 폼 구현
        with st.form(key='signup_form'):
            username = st.text_input('아이디')
            password = st.text_input('비밀번호', type='password')
            confirm_password = st.text_input('비밀번호 확인', type='password')
            name = st.text_input('이름')
            age_options = ["0-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71+"]
            age = st.selectbox('나이', age_options)
            email = st.text_input('이메일')
            guardian_email = st.text_input('보호자 이메일')
            phone_number = st.text_input('전화번호')

            usage_purpose = st.selectbox('사용 목적', ['노이즈캔슬링 보조 장치', '청각 보조 장치', '기타'])

            signup_button = st.form_submit_button('가입하기')

        if signup_button:
            if password == confirm_password:
                # 세션 상태에 사용자 정보 저장
                st.session_state.user_info = {
                    'id': username,
                    'password': password,
                    'name': name,
                    'age': age,
                    'email': email,
                    'guardian_email': guardian_email,
                    'phone_number': phone_number,
                    'usage_purpose': usage_purpose
                }
                st.success(f'{name}님, 회원가입을 축하합니다!')
                # st.query_params.update(page="Home")
            else:
                st.error('비밀번호가 일치하지 않습니다.')