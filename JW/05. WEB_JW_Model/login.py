import streamlit as st

class Login_page:
    def __init__(self):
        # 초기화는 객체 생성 시 한 번만 호출되고, run에서 페이지 로직을 처리합니다.
        pass
    def run(self):
        st.header("🔊 로그인")
        with st.form(key='login_form'):
            username = st.text_input('아이디')
            password = st.text_input('비밀번호', type='password')
            submit_button = st.form_submit_button('로그인')

        if submit_button:
            # 세션 상태에서 사용자 정보 가져오기
            if 'user_info' in st.session_state:
                if st.session_state.user_info['id'] == username and st.session_state.user_info['password'] == password:
                    st.success('로그인 성공!')
                    st.session_state.page = 'Home'
                    st.rerun()
                else:
                    st.error('로그인 실패. 아이디 또는 비밀번호를 확인해주세요.')
            else:
                st.error('회원가입 후 로그인 해주세요.')

