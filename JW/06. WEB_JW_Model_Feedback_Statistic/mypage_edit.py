import streamlit as st

class Edit_page:
    def __init__(self):
        # 초기화는 객체 생성 시 한 번만 호출되고, run에서 페이지 로직을 처리합니다.
        pass

    def run(self):
        st.header("📝 회원 정보 수정")
        
        # 세션 상태에서 회원 정보 가져오기 (예시)
        if 'user_info' in st.session_state:
            user_info = st.session_state.user_info
        else:
            st.warning("로그인 후 이용해주세요.")
            st.stop()

        with st.form(key='edit_form'):
            # 변경 불가능한 필드
            st.text_input('아이디 (변경 불가)', value=user_info['id'], disabled=True)
            st.text_input('이메일 (변경 불가)', value=user_info['email'], disabled=True)

            # 변경 가능한 필드
            password = st.text_input('비밀번호', type='password', value=user_info['password'])
            password_confirm = st.text_input('비밀번호 확인', type='password', value=user_info['password']) # 초기값을 비밀번호와 같게 설정
            name = st.text_input('이름', value=user_info['name'])
            age_options = ["0-20", "21-30", "31-40", "41-50", "51-60", "61-70", "71+"]
            age = st.selectbox('나이', age_options, index=age_options.index(user_info['age'])) # 기존 나이 선택
            guardian_email = st.text_input('보호자 이메일', value=user_info['guardian_email'])
            phone_number = st.text_input('전화번호', value=user_info['phone_number'])
            usage_purpose = st.selectbox('사용 목적', ['노이즈캔슬링 보조 장치', '청각 보조 장치', '기타'], index=['노이즈캔슬링 보조 장치', '청각 보조 장치', '기타'].index(user_info['usage_purpose'])) # 기존 사용 목적 선택

            submit_button = st.form_submit_button('수정')

        if submit_button:
            if password == password_confirm:
                # 수정된 정보 업데이트 로직 (데이터베이스 업데이트 등)
                st.success('회원 정보가 수정되었습니다!')
                # session에 저장된 정보도 업데이트
                st.session_state.user_info['password'] = password
                st.session_state.user_info['name'] = name
                st.session_state.user_info['age'] = age
                st.session_state.user_info['guardian_email'] = guardian_email
                st.session_state.user_info['phone_number'] = phone_number
                st.session_state.user_info['usage_purpose'] = usage_purpose
                st.rerun()
            else:
                st.error('비밀번호와 비밀번호 확인이 일치하지 않습니다.')

        if st.button('Home으으로 돌아가기'):
            st.session_state.page = 'Home'
            st.rerun()
