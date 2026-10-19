# CPI 항목 정의 — 코드, 표기명, 버킷, 설명
# code: BLS item code (CUSR0000/CUUR0000 뒤에 붙는 부분)
# t2: BLS 보도자료 표1·표2의 항목명 (가중치 매칭용)
# bucket: food / energy / core_goods / shelter / core_svc (주거 제외 근원 서비스)

AGGREGATES = [
    # code, t2 이름, 한글명
    ("SA0", "All items", "전체 CPI"),
    ("SA0L1E", "All items less food and energy", "근원 CPI"),
    ("SAF1", "Food", "식품"),
    ("SA0E", "Energy", "에너지"),
    ("SACL1E", "Commodities less food and energy commodities", "근원 상품"),
    ("SASLE", "Services less energy services", "근원 서비스"),
    ("SAH1", "Shelter", "주거비"),
    ("SAS4", "Transportation services", "교통 서비스"),
]

# 가중치 차감으로 만드는 파생 시리즈: (code, 한글명, base, minus 목록, 설명)
DERIVED = [
    ("SUPERCORE", "슈퍼코어 (주거 제외 근원 서비스)", "SASLE", ["SAH1"],
     "근원 서비스에서 주거비를 뺀 것. 임금과 연결돼 연준이 가장 신경 쓰는 서비스 물가다. 의료·자동차보험·항공료·오락·교육 등이 들어간다."),
    ("COREGX_VEH", "차량 제외 근원 상품", "SACL1E", ["SETA01", "SETA02"],
     "근원 상품에서 신차·중고차를 뺀 것. 차량 가격의 큰 변동을 걷어내고 관세가 의류·가구·가전 등 일반 상품에 옮겨붙는지 볼 때 쓴다."),
    ("SHELTER_XL", "숙박 제외 주거비", "SAH1", ["SEHB"],
     "주거비에서 호텔·숙박을 뺀 것. 숙박은 여행 수요에 따라 크게 출렁여서, 빼야 집세·자가주거비 추세가 깨끗하게 보인다."),
    ("TRANS_OTH", "기타 교통서비스", "SAS4", ["SETE", "SETD", "SETG01"],
     "교통 서비스에서 자동차보험·정비·항공료를 뺀 나머지. 차량 리스·렌트, 대중교통, 차량 등록·주차비 등이다."),
]

ITEMS = [
    # ---- 식품 ----
    dict(code="SAF11", t2="Food at home", ko="식료품 (가정용)", bucket="food", kind="goods",
         desc="마트에서 사는 식재료. 곡물·육류·유제품·채소·과일·음료 등. 날씨·작황·환율·관세 영향을 크게 받아 변동이 크다."),
    dict(code="SEFV", t2="Food away from home", ko="외식", bucket="food", kind="services",
         desc="식당·패스트푸드·급식 등 밖에서 사 먹는 음식. 인건비 비중이 커서 임금 상승이 서서히, 오래 반영된다."),
    # ---- 에너지 ----
    dict(code="SETB", t2="Motor fuel", ko="자동차 연료 (휘발유 등)", bucket="energy", kind="goods",
         desc="휘발유·경유 등. 국제유가를 거의 그대로 따라가서 헤드라인 CPI의 월별 변동을 가장 크게 만든다."),
    dict(code="SEHE", t2="Fuel oil and other fuels", ko="난방유·기타 연료", bucket="energy", kind="goods",
         desc="가정 난방유·프로판 등. 비중은 작지만 유가에 민감하다."),
    dict(code="SEHF01", t2="Electricity", ko="전기료", bucket="energy", kind="services",
         desc="가정용 전기요금. 천연가스 가격과 전력 수요(데이터센터 등), 주별 요금 인가에 따라 움직인다."),
    dict(code="SEHF02", t2="Utility (piped) gas service", ko="도시가스", bucket="energy", kind="services",
         desc="배관으로 공급되는 가정용 가스요금. 천연가스 가격을 시차를 두고 따라간다."),
    # ---- 근원 상품 ----
    dict(code="SETA01", t2="New vehicles", ko="신차", bucket="core_goods", kind="goods",
         desc="새 자동차·트럭 가격. 딜러 할인·인센티브와 수입차 관세에 영향을 받는다."),
    dict(code="SETA02", t2="Used cars and trucks", ko="중고차", bucket="core_goods", kind="goods",
         desc="중고 차량 가격. 경매 가격(만하임 지수)을 1~2개월 시차로 따라가며 변동이 매우 크다."),
    dict(code="SETC", t2="Motor vehicle parts and equipment", ko="차량 부품", bucket="core_goods", kind="goods",
         desc="타이어·부품·액세서리. 수입 비중이 높아 관세 전이가 빨리 나타나는 품목이다."),
    dict(code="SAA", t2="Apparel", ko="의류", bucket="core_goods", kind="goods",
         desc="옷·신발·보석. 대부분 수입품이라 관세 영향을 보는 대표 품목이다. 계절 할인 때문에 원계열 변동이 크다."),
    dict(code="SAH31", t2="Household furnishings and supplies", ko="가구·가정용품", bucket="core_goods", kind="goods",
         desc="가구·침구·가전·주방용품·청소용품. 수입 비중이 높아 관세 전이 확인용."),
    dict(code="SAM1", t2="Medical care commodities", ko="의약품", bucket="core_goods", kind="goods",
         desc="처방약·일반의약품·의료용품. 약가 정책과 제네릭 출시에 따라 움직인다."),
    dict(code="SARC", t2="Recreation commodities", ko="오락 용품", bucket="core_goods", kind="goods",
         desc="TV·음향기기·장난감·스포츠용품·반려동물 용품·도서 등."),
    dict(code="SAE1", t2="Education and communication commodities", ko="IT기기·교재", bucket="core_goods", kind="goods",
         desc="컴퓨터·스마트폰·소프트웨어·교재. 품질 개선이 가격 하락으로 반영돼 장기적으로 내려가는 경향."),
    dict(code="SAF116", t2="Alcoholic beverages", ko="주류", bucket="core_goods", kind="goods",
         desc="가정·외식 주류."),
    dict(code="SAGC", t2="Other goods", ko="기타 상품 (담배·개인용품)", bucket="core_goods", kind="goods",
         desc="담배, 화장품·세면용품 등 개인관리 용품, 문구 등."),
    # ---- 주거 ----
    dict(code="SEHC", t2="Owners' equivalent rent of residences", ko="자가주거비 (OER)", bucket="shelter", kind="services",
         desc="자기 집에 사는 사람이 '그 집을 빌린다면 낼 임대료'를 추정한 값. 실제로 돈이 오가지 않는 가상의 비용이다. "
              "집값이 아니라 비슷한 임대주택의 실제 집세 표본으로 계산하므로 집세(아래)와 같은 방향으로 움직이지만 가중치가 3배 이상 크다. "
              "표본을 6개 그룹으로 나눠 그룹마다 6개월에 한 번 조사하고, 매달 6개월 변화의 6제곱근을 쓰기 때문에 시장 임대료를 6~12개월 늦게 따라간다."),
    dict(code="SEHA", t2="Rent of primary residence", ko="집세 (실제 임대료)", bucket="shelter", kind="services",
         desc="세입자가 실제로 내는 월세. 자가주거비와 같은 표본을 쓰지만 실제 거래 임대료다. "
              "자가주거비와 계산 방식이 거의 같아서 둘이 갑자기 벌어지면 가중치 구조나 표본 그룹 차이(일회성) 가능성을 의심한다. "
              "질로·아파트먼트리스트 같은 시장 신규 임대료 지수를 약 1년 늦게 따라간다."),
    dict(code="SEHB", t2="Lodging away from home", ko="호텔·숙박", bucket="shelter", kind="services",
         desc="호텔·모텔·기숙사 등. 여행 수요와 이벤트에 따라 크게 출렁이는 대표적인 '일회성' 후보."),
    dict(code="SEHD", t2="Tenants' and household insurance", ko="세입자·주택 보험", bucket="shelter", kind="services",
         desc="세입자 보험·주택 내용물 보험. 비중이 작다. 계절조정 시리즈가 없어 원계열을 쓴다."),
    # ---- 근원 서비스 (주거 제외) ----
    dict(code="SAM2", t2="Medical care services", ko="의료 서비스", bucket="core_svc", kind="services",
         desc="진료비·병원비·건강보험. 병원 요금 인상은 연초나 계약 갱신 때 몰려서 계단식으로 움직인다. "
              "건강보험은 보험사 이익잉여금을 쓰는 간접 방식이라 연 1회 수치가 바뀌며 꺾이는 시점이 늦다."),
    dict(code="SETE", t2="Motor vehicle insurance", ko="자동차보험", bucket="core_svc", kind="services",
         desc="자동차보험료. 차량·수리비 상승이 1~2년 뒤 보험료로 넘어온다. 주별 요율 승인이 한꺼번에 반영되면 튄다."),
    dict(code="SETD", t2="Motor vehicle maintenance and repair", ko="차량 정비·수리", bucket="core_svc", kind="services",
         desc="정비소 공임·수리비. 인건비와 부품 가격(관세)을 함께 반영한다."),
    dict(code="SETG01", t2="Airline fares", ko="항공료", bucket="core_svc", kind="services",
         desc="국내·국제 항공권. 제트유 가격과 여행 수요에 따라 월별 변동이 매우 큰 대표적인 일회성 항목."),
    dict(code="TRANS_OTH", t2=None, ko="기타 교통서비스", bucket="core_svc", kind="services", derived=True,
         desc="차량 리스·렌트, 대중교통, 차량 등록·주차비 등. 교통 서비스에서 위 세 항목을 빼서 계산."),
    dict(code="SEHG", t2="Water and sewer and trash collection services", ko="상하수도·쓰레기", bucket="core_svc", kind="services",
         desc="수도·하수도·쓰레기 수거 요금. 지자체 요금 인상 시점에 계단식으로 오른다."),
    dict(code="SARS", t2="Recreation services", ko="오락 서비스", bucket="core_svc", kind="services",
         desc="스트리밍·케이블, 헬스장·클럽 회비, 공연·스포츠 입장료, 반려동물 진료 등."),
    dict(code="SEEB", t2="Tuition, other school fees, and childcare", ko="등록금·보육", bucket="core_svc", kind="services",
         desc="대학·초중고 등록금, 어린이집 비용. 학기 시작(8~9월)에 몰려서 오른다."),
    dict(code="SEED", t2="Telephone services", ko="통신 (휴대폰·유선)", bucket="core_svc", kind="services",
         desc="휴대폰·유선전화 요금. 통신사 요금제 개편이 한 달에 몰려 반영되면 크게 튀었다가 되돌아간다(2026년 8월 사례)."),
    dict(code="SEEE03", t2="Internet services and electronic information providers", ko="인터넷", bucket="core_svc", kind="services",
         desc="가정용 인터넷 요금. 속도 개선이 품질 조정으로 반영돼 하락하는 경향이 있다."),
    dict(code="SAGS", t2="Other personal services", ko="기타 개인서비스", bucket="core_svc", kind="services",
         desc="미용실·세탁·장례·법률·은행 수수료 등. 인건비 비중이 높다. 계절조정 시리즈가 없어 원계열을 쓴다."),
]

# 의료 서비스 하위 (참고용, 합계에서 제외)
CHILDREN = [
    dict(code="SEMC01", t2="Physicians' services", ko="└ 의사 진료", parent="SAM2",
         desc="의사 진료비. 메디케어 수가 조정이 연초에 반영된다."),
    dict(code="SEMD01", t2="Hospital services", ko="└ 병원 서비스", parent="SAM2",
         desc="입원·외래 병원비. 병원과 보험사의 계약 갱신 시점에 계단식으로 오른다."),
    dict(code="SEME", t2="Health insurance", ko="└ 건강보험", parent="SAM2",
         desc="보험사 이익잉여금으로 추정하는 간접 방식. 매년 10월에 새 데이터로 바뀌어 연 1회 방향이 바뀐다."),
]

BUCKETS = [
    ("food", "식품", "#f2b84b"),
    ("energy", "에너지", "#8d99ae"),
    ("core_goods", "근원 상품", "#5aa9e6"),
    ("shelter", "주거비", "#e76f51"),
    ("core_svc", "주거 제외 근원 서비스", "#c77dff"),
]

BUCKET_DESC = {
    "food": "식료품과 외식. 근원 CPI에서는 빠진다.",
    "energy": "휘발유·전기·가스 등. 유가에 따라 크게 출렁여서 근원 CPI에서는 빠진다.",
    "core_goods": "식품·에너지를 뺀 상품. 차량·의류·가구·가전·의약품 등. 관세 전이가 먼저 보이는 곳이다.",
    "shelter": "자가주거비·집세·숙박. 근원 CPI의 40% 넘게 차지하는 가장 큰 덩어리이며, 시장 임대료를 6~12개월 늦게 따라간다.",
    "core_svc": "주거비를 뺀 근원 서비스(슈퍼코어). 의료·보험·교통·교육·오락 등. 임금과 연결돼 끈적하다.",
}
