import streamlit as st
import mysql.connector
from config import DB_CONFIG

class Login_page:
    def __init__(self):
        self.db_connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port']
        )
        self.cursor = self.db_connection.cursor(dictionary=True)


    def user_login(self, username, password):
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        self.cursor.execute(query, (username, password))
        user = self.cursor.fetchone()
        return user
    
    def run(self):
        st.header("🔊 로그인")

        with st.form(key='login_form'):
            username = st.text_input('아이디')
            password = st.text_input('비밀번호', type='password')
            submit_button = st.form_submit_button('로그인')

        if submit_button:
            user = self.user_login(username, password)
            # 세션 상태에서 사용자 정보 가져오기
            if user:
                st.session_state['user_info'] = user
                st.success(f"로그인 성공! 환영합니다, {user['name']}님!")
            else:
                st.error('로그인 실패. 아이디 또는 비밀번호를 확인해주세요.')
