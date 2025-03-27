import streamlit as st
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


def set_default_alarm_settings(user_id):
    DEFAULT_ALARM_DB = {
        "차량경적": 100,
        "이륜차경적": 100,
        "차량사이렌": 110,
        "차량주행음": 90,
        "이륜차주행음": 90,
        "기타소음": 85
    }
    
    selected_sensitivity = "중(🟡)"  # 기본 감도 "중(🟡)"로 설정
    
    # 기본 데시벨 값 적용 (감도에 따라 값이 조정됨)
    adjusted_alarm_settings = {
        noise_type: {
            "데시벨": DEFAULT_ALARM_DB[noise_type] + {"약(🔵)": -10, "중(🟡)": 0, "강(🔴)": 10}[selected_sensitivity]
        }
        for noise_type in DEFAULT_ALARM_DB
    }
    
    # 기본 알람 설정 DB 저장 (save_alarm_settings 함수 사용)
    for noise_type, values in adjusted_alarm_settings.items():
        save_alarm_settings(
            user_id=user_id,
            noise_type=noise_type,
            alarm_db=values["데시벨"],
            sensitivity_level=selected_sensitivity
        )

# 알람 설정 저장 함수
def save_alarm_settings(user_id, noise_type, alarm_db, sensitivity_level):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # 이미 존재하는지 확인
    cursor.execute("SELECT user_id FROM alarm_settings WHERE user_id = %s AND noise_type = %s", (user_id, noise_type))
    existing_record = cursor.fetchone()

    if existing_record:
        query = """
            UPDATE alarm_settings
            SET alarm_db = %s, sensitivity_level = %s
            WHERE user_id = %s AND noise_type = %s
        """
        values = (alarm_db, sensitivity_level, user_id, noise_type)
        cursor.execute(query, values)
    else:
        query = """
            INSERT INTO alarm_settings (user_id, noise_type, alarm_db, sensitivity_level)
            VALUES (%s, %s, %s, %s)
        """
        values = (user_id, noise_type, alarm_db, sensitivity_level)
        cursor.execute(query, values)
    conn.commit()
    conn.close()


class Signup_page():
    def __init__(self):
        self.db_connection = None
    
    def connect_db(self):
        try:
            self.db_connection = mysql.connector.connect(
                host=DB_CONFIG['host'],        # MySQL 서버 주소
                user=DB_CONFIG['user'],        # MySQL 사용자명
                password=DB_CONFIG['password'],# MySQL 비밀번호
                database=DB_CONFIG['database'],# 데이터베이스 이름
                port=DB_CONFIG['port'], # MySQL 포트
            )
            
        except Error as e:
            st.error(f"DB 연결 오류: {e}")
            self.db_connection = None
        
    def save_to_db(self, user_info):
        if self.db_connection:
            cursor = self.db_connection.cursor()
            query = """INSERT INTO users (username, password, name, age, email, guardian_email, phone_number, usage_purpose)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            try:
                cursor.execute(query, (
                    user_info['username'], 
                    user_info['password'], 
                    user_info['name'], 
                    user_info['age'],
                    user_info['email'], 
                    user_info['guardian_email'], 
                    user_info['phone_number'], 
                    user_info['usage_purpose']
                ))
                self.db_connection.commit()
                # 새로 생성된 사용자 ID를 가져와서 user_info에 저장
                new_id = cursor.lastrowid

                user_info['id'] = new_id
            except Error as e:
                st.error(f"DB에 저장하는 중 오류 발생: {e}")
            finally:
                cursor.close()
    
    def is_username_taken(self, username):
        """중복된 username이 있는지 확인"""
        if not self.db_connection:
            self.connect_db()
        cursor = self.db_connection.cursor()
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()[0]
        cursor.close()
        return result > 0


    def run(self):        
        st.header("📝 회원가입")
        
        # 회원가입 폼 구현
        with st.form(key='signup_form'):
            username = st.text_input('아이디', placeholder="아이디를 입력하세요")
            password = st.text_input('비밀번호', type='password', placeholder="비밀번호를 입력하세요")
            confirm_password = st.text_input('비밀번호 확인', type='password', placeholder="비밀번호를 다시 입력하세요")
            name = st.text_input('이름', placeholder="이름을 입력하세요")
            age_options = ["0-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71+"]
            age = st.selectbox('나이', age_options)
                            
            options=['@gmail.com', '@naver.com', '@daum.net', '@nate.com']
            col1, col2 = st.columns(2)
            with col1:
                email_local = st.text_input('이메일', placeholder="이메일을 입력하세요")
            with col2:
                types = st.selectbox('도메인', options, key='email_domain')
            email = email_local + types
        
            col1, col2 = st.columns(2)
            with col1:
                guardian_local = st.text_input('보호자 이메일', placeholder="⚠️ 보호자 이메일을 정확히 입력해주세요", help="⚠️ 보호자 이메일을 정확히 입력해야 사용자 긴급 상황 발생 시 보호자에게 SOS 이메일이 정상적으로 전송됩니다.")  
            with col2:
                types2 = st.selectbox('도메인',options, key='guardian_email_domain')
            guardian_email = guardian_local + types2 
                        
            phone_number = st.text_input('전화번호', placeholder="⚠️ 전화번호를 정확히 입력해주세요", help="⚠️ 긴급 상황 발생 SOS 이메일 전송 시, 보호자에게 사용자의 전화번호 정보가 함께 제공됩니다.")
            usage_purpose = st.selectbox('사용 목적', ['노이즈캔슬링 보조 장치', '청각 보조 장치', '기타'])

            signup_button = st.form_submit_button('가입하기')
            
            
        if signup_button:
            # 빈 입력 필드 확인
            missing_fields = []
            if not username:
                missing_fields.append("아이디")
            if not password:
                missing_fields.append("비밀번호")
            if not confirm_password:
                missing_fields.append("비밀번호 확인")
            if not name:
                missing_fields.append("이름")
            if not email_local:
                missing_fields.append("이메일")
            if not guardian_local:
                missing_fields.append("보호자 이메일")
            if not phone_number:
                missing_fields.append("전화번호")

            if missing_fields:
                st.error(f"{', '.join(missing_fields)} 입력해야 합니다.")
                return

            # 비밀번호 일치 확인
            if password != confirm_password:
                st.error('비밀번호가 일치하지 않습니다.')
                return
            if self.is_username_taken(username):
                st.error("❌ 해당 아이디는 이미 사용 중입니다. 다른 아이디를 입력해주세요.")
                return

            # 세션 상태에 사용자 정보 저장
            st.session_state.user_info = {
                'username': username,
                'password': password,
                'name': name,
                'age': age,
                'email': email,
                'guardian_email': guardian_email,
                'phone_number': phone_number,
                'usage_purpose': usage_purpose
            }
            
            user_info = st.session_state.user_info
            self.connect_db()  
            self.save_to_db(user_info)  
            st.session_state.user_info = user_info
            
            # user_info에 'id' 키가 있는지 확인
            if 'id' in user_info:
                st.session_state.user_id = user_info['id']
                set_default_alarm_settings(user_info['id'])
            else:
                st.error("사용자 ID가 저장되지 않았습니다.")
                                        
            # 자동 로그인 처리
            st.success(f'{name}님, 회원가입을 축하합니다!')
            st.session_state.logged_in = True