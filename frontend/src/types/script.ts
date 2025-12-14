export interface ScriptLine {
  emotion: string; // 감정 (공통)
  text: string;
  pronunciation?: string;
}

export interface ScriptSection {
  emoji: string;
  title: string;
  lines: ScriptLine[];
}
export const KOREAN_SCRIPT_EXTENDED = [
  {
    emoji: "🌙",
    title: "달빛 숲의 작은 여우",
    lines: [
      {
        emotion: "부드럽고 신비로운 시작",
        text: "옛날 옛적, 은빛 달빛이 쏟아지는 깊은 숲 속에 작은 여우가 살고 있었어요.",
      },
      {
        emotion: "애정, 따뜻함",
        text: "이름은 루나. 루나는 세상에서 가장 호기심이 많고, 늘 새로운 것을 찾아다니는 모험가였답니다.",
      },
      {
        emotion: "장난스러움",
        text: "루나는 반짝이는 것이라면 뭐든지 좋아했어요. 이슬 맺힌 거미줄도, 숲 속을 나는 반딧불이도, 멀리 있는 별도요!",
      },
      {
        emotion: "평화로운 분위기 강조",
        text: "그날도 루나는 나무 그늘 아래서 조용히 밤의 소리를 듣고 있었어요.",
      },
      {
        emotion: "흥분, 놀라움",
        text: "바로 그때, 루나는 하늘에서 믿을 수 없는 무언가가 떨어지는 걸 보았어요. 슈우우욱! 거대한 소리와 함께요!",
      },
      {
        emotion: "호기심 가득",
        text: '"저게 대체 뭘까? 설마 별이 떨어진 걸까? 꼭 가서 확인해봐야겠어!"',
      },
    ],
  },
  {
    emoji: "⭐",
    title: "별똥별과의 만남",
    lines: [
      {
        emotion: "서두름, 설렘",
        text: "루나는 작은 발로 폴짝폴짝 뛰어갔어요. 나뭇잎을 바스락바스락 밟으며 떨어진 곳을 향해 달려갔죠.",
      },
      {
        emotion: "경이로움",
        text: "그리고 숲 속 빈터에서, 손바닥만 한 크기의 작은 별똥별을 발견했답니다. 푸른빛과 금빛으로 반짝반짝 빛나고 있었어요!",
      },
      {
        emotion: "걱정, 염려",
        text: '"아이고, 다쳤니? 너 엄청 아파 보여." 루나가 작은 코를 킁킁거리며 조심스럽게 물었어요.',
      },
      {
        emotion: "약한 목소리, 슬픔",
        text: '별똥별이 작은 목소리로 대답했어요. "응... 발목을 삐끗한 것 같아. 집인 하늘로 돌아가고 싶은데, 너무 멀리 떨어져버렸어."',
      },
      {
        emotion: "안쓰러움, 공감",
        text: "루나는 슬퍼하는 별똥별을 보자 마음이 아팠어요. 집에 가고 싶은 마음이 얼마나 간절할지 알았거든요.",
      },
      {
        emotion: "결심, 용기",
        text: '루나는 큰 눈을 깜빡이며 단호하게 말했어요. "걱정 마! 내가 루나잖아! 반드시 방법을 찾아서 널 도와줄게!"',
      },
    ],
  },
  {
    emoji: "🦉",
    title: "지혜로운 부엉이 할아버지",
    lines: [
      {
        emotion: "생각하는 모습",
        text: "하지만 루나는 어떻게 해야 별을 하늘로 돌려보낼 수 있을지 도저히 몰랐어요.",
      },
      {
        emotion: "아이디어 떠오름",
        text: '"맞다! 이런 어려운 일은 부엉이 할아버지께 여쭤봐야지! 할아버지는 모든 것을 아시니까!"',
      },
      {
        emotion: "존경, 공손함",
        text: "루나는 별똥별을 조심스럽게 등에 업고 숲에서 가장 크고 오래된 참나무로 갔어요. 그곳엔 아주 지혜로운 부엉이 할아버지가 사셨답니다.",
      },
      {
        emotion: "낮고 온화한 목소리",
        text: '"호오... 달빛 숲의 작은 여우가 하늘의 길을 묻는구나. 별을 집으로 보내주고 싶다고?" 부엉이 할아버지가 천천히 루나를 바라보며 말씀하셨어요.',
      },
      {
        emotion: "신비로움",
        text: '"너의 친절함이 참으로 귀하구나. 가장 높은 \'빛의 산\' 꼭대기로 가거라. 그곳에서 진심을 담아 소원을 빌면, 네 용기가 하늘에 닿아 별을 되돌려 줄 것이다."',
      },
    ],
  },
  {
    emoji: "⛰️",
    title: "험난한 모험",
    lines: [
      {
        emotion: "두려움, 떨림",
        text: "가장 높은 산이라니... 루나는 태어나서 한 번도 그렇게 멀고 험한 곳을 가본 적이 없었어요. 발이 후들후들 떨렸죠.",
      },
      {
        emotion: "위로, 격려",
        text: '별똥별이 루나의 등에서 빛을 내며 속삭였어요. "루나, 무서우면 안 가도 돼. 넌 이미 나에게 충분히 친절했어."',
      },
      {
        emotion: "단호함, 용기",
        text: '하지만 루나는 고개를 단호하게 저었어요. "아니야! 친구를 절대로 포기하지 않을 거야. 함께 가자, 별똥별!"',
      },
      {
        emotion: "힘든 여정",
        text: "산길은 예상보다 훨씬 험했어요. 바위는 미끄럽고, 길은 가파르고, 밤바람은 세차게 불었어요. 휘이이익!",
      },
      {
        emotion: "내면의 투지",
        text: "루나는 숨을 헐떡였지만, 등에 업힌 별똥별이 따뜻하게 빛나는 것을 보며 힘을 냈어요. '조금만 더, 조금만 더!'",
      },
      {
        emotion: "응원",
        text: '별똥별이 따뜻하게 빛나며 말했어요. "루나, 넌 정말 용감한 영웅이야! 우리 이제 정말로 거의 다 왔어!"',
      },
    ],
  },
  {
    emoji: "✨",
    title: "마법 같은 순간",
    lines: [
      {
        emotion: "감동, 경외",
        text: "마침내, 새벽이 밝아오기 전 산 꼭대기에 도착했어요. 발밑으로는 구름이 깔려있고 하늘이 정말 가까웠어요!",
      },
      {
        emotion: "진지함, 간절함",
        text: "루나는 눈을 꼭 감고, 별똥별을 양손으로 감싸 안으며 온 마음과 진심을 담아 소원을 빌었어요.",
      },
      {
        emotion: "속삭이듯",
        text: '"사랑하는 별아, 네 집인 하늘로 무사히 돌아가렴. 넌 저 위에서 모두를 위해 빛나야 해."',
      },
      {
        emotion: "마법적, 신비로움",
        text: "그 순간, 별똥별이 온 세상을 밝힐 듯 환하게 빛나기 시작했어요. 반짝, 반짝, 반짝!",
      },
      {
        emotion: "놀라움, 기쁨",
        text: "그리고 천천히, 아주 우아하게, 무중력처럼 하늘로 떠올랐답니다. 루나의 얼굴에 눈물이 맺혔어요.",
      },
      {
        emotion: "아쉬움, 따뜻함",
        text: '"루나, 정말 고마워! 네 친절함을 절대 잊지 않을게!" 별똥별이 루나에게 마지막 작별 인사를 외쳤어요.',
      },
    ],
  },
  {
    emoji: "💫",
    title: "특별한 선물",
    lines: [
      {
        emotion: "감동적",
        text: "별똥별은 하늘로 빠르게 올라가면서도, 작별 선물처럼 작은 빛 가루를 루나에게 흩뿌려주었어요.",
      },
      {
        emotion: "놀라움, 신기함",
        text: "그러자 루나의 꼬리 끝이 마치 작은 은하수처럼 은은하게 빛나기 시작했어요!",
      },
      {
        emotion: "기쁨 폭발",
        text: '"와아! 나도 이제 반짝반짝 빛나! 정말 멋진걸!" 루나가 신이 나서 꼬리를 흔들며 소리쳤어요.',
      },
      {
        emotion: "멀리서 들려오는 목소리",
        text: '하늘 높은 곳에서 별똥별의 따뜻한 목소리가 들려왔어요. "이 빛은 네 용기의 증표야! 이젠 너도 하늘처럼 특별한 친구야!"',
      },
      {
        emotion: "벅찬 감동",
        text: "루나는 그 빛나는 꼬리를 물끄러미 바라보며 가슴이 벅차올랐답니다.",
      },
    ],
  },
  {
    emoji: "🏡",
    title: "따뜻한 결말",
    lines: [
      {
        emotion: "만족스러움",
        text: "루나는 빛나는 꼬리를 뒤로하고, 무거운 발걸음으로 집인 달빛 숲으로 돌아왔어요.",
      },
      {
        emotion: "피곤하지만 행복함",
        text: "온몸은 지쳤고 다리는 쑤셨지만, 마음속은 그 어떤 날보다 포근하고 따뜻했답니다.",
      },
      {
        emotion: "깨달음",
        text: "루나는 이번 모험을 통해 깨달았어요. 물질적인 보물보다 누군가를 조건 없이 도와주는 것이 세상에서 가장 값지고 빛나는 일이라는 걸요.",
      },
      {
        emotion: "부드러운 마무리",
        text: "그날 밤부터 루나는 그저 평범한 여우가 아니었어요. 숲의 모든 동물들이 루나를 용감한 영웅으로 존경했죠.",
      },
      {
        emotion: "따뜻한 종결",
        text: "달빛 아래서 은은하게 빛나는 꼬리를 가진, 친절함과 용기를 겸비한 작은 여우로요.",
      },
      {
        emotion: "자장가 같은 엔딩",
        text: "그리고 밤하늘의 수많은 별들은 루나를 지켜보며 영원히 반짝였답니다. 루나의 이야기는 숲 속에 오래오래 전해졌어요. 끝.",
      },
    ],
  },
];

export const ENGLISH_SCRIPT_EXTENDED = [
  {
    emoji: "🌙",
    title: "Luna the Little Fox in Moonlight Forest",
    lines: [
      {
        emotion: "부드럽고 신비로운 시작",
        text: "Once upon a time, in a deep forest filled with silvery moonlight, there lived a little fox.",
        pronunciation:
          "원스 어폰 어 타임, 인 어 딥 포레스트 필드 윗 실버리 문라이트, 데어 리브드 어 리틀 폭스.",
      },
      {
        emotion: "애정, 따뜻함",
        text: "Her name was Luna. Luna was the most curious fox in the world, always searching for new adventures.",
        pronunciation:
          "허 네임 워즈 루나. 루나 워즈 더 모스트 큐리어스 폭스 인 더 월드, 올웨이즈 써칭 포 뉴 어드벤쳐스.",
      },
      {
        emotion: "장난스러움",
        text: "Luna loved anything that sparkled. Dewdrops on spider webs, fireflies dancing in the air, and distant stars!",
        pronunciation:
          "루나 러브드 애니씽 댓 스파클드. 듀드랍스 온 스파이더 웹스, 파이어플라이즈 댄싱 인 디 에어, 앤 디스턴트 스타즈!",
      },
      {
        emotion: "평화로운 분위기 강조",
        text: "On that particular evening, Luna was sitting quietly under a tree, listening to the sounds of the night.",
        pronunciation:
          "온 댓 퍼티큘러 이브닝, 루나 워즈 싯팅 콰이어틀리 언더 어 트리, 리스닝 투 더 사운즈 오브 더 나잇.",
      },
      {
        emotion: "흥분, 놀라움",
        text: "Suddenly, Luna saw something unbelievable fall from the sky. Whoooosh! It made a huge sound!",
        pronunciation:
          "서든리, 루나 쏘 썸씽 언빌리버블 폴 프럼 더 스카이. 후우우우쉬! 잇 메이드 어 휴즈 사운드!",
      },
      {
        emotion: "호기심 가득",
        text: '"What on earth could that be? A falling star? I simply must go check it out!"',
        pronunciation:
          '"왓 온 얼쓰 쿠드 댓 비? 어 폴링 스타? 아이 심플리 머스트 고우 첵 잇 아웃!"',
      },
    ],
  },
  {
    emoji: "⭐",
    title: "Meeting the Shooting Star",
    lines: [
      {
        emotion: "서두름, 설렘",
        text: "Luna hopped along quickly on her tiny paws. Rustle, rustle, went the leaves as she ran toward the spot.",
        pronunciation:
          "루나 합트 얼롱 퀵클리 온 허 타이니 포즈. 러슬, 러슬, 웬트 더 리브즈 애즈 쉬 랜 투워드 더 스팟.",
      },
      {
        emotion: "경이로움",
        text: "And there, in a forest clearing, she found a tiny shooting star, no bigger than her paw. It was twinkling with blue and gold light!",
        pronunciation:
          "앤 데어, 인 어 포레스트 클리어링, 쉬 파운드 어 타이니 슈팅 스타, 노우 비거 댄 허 포. 잇 워즈 트윙클링 윗 블루 앤 골드 라잇!",
      },
      {
        emotion: "걱정, 염려",
        text: '"Oh my, are you hurt? You look terribly sore." Luna sniffed gently.',
        pronunciation:
          '"오우 마이, 아 유 헐트? 유 룩 테러블리 쏘어." 루나 스닙트 젠틀리.',
      },
      {
        emotion: "약한 목소리, 슬픔",
        text: 'The shooting star answered in a tiny, sad voice. "Yes... I think I twisted my ankle. I want to go home to the sky, but I fell so far down."',
        pronunciation:
          '더 슈팅 스타 앤서드 인 어 타이니, 새드 보이스. "예스... 아이 띵크 아이 트위스티드 마이 앵클. 아이 원트 투 고우 홈 투 더 스카이, 벗 아이 펠 쏘 파 다운."',
      },
      {
        emotion: "안쓰러움, 공감",
        text: "Luna's heart ached for the sad little star. She understood how much it must miss its home.",
        pronunciation:
          "루나즈 하트 에익트 포 더 새드 리틀 스타. 쉬 언더스투드 하우 머치 잇 머스트 미스 잇츠 홈.",
      },
      {
        emotion: "결심, 용기",
        text: 'Luna blinked her big eyes and declared firmly, "Don\'t worry! I am Luna! I will certainly find a way to help you!"',
        pronunciation:
          '루나 블링크트 허 빅 아이즈 앤 디클레어드 펌리, "돈트 워리! 아이 앰 루나! 아일 썰튼리 파인드 어 웨이 투 헬프 유!"',
      },
    ],
  },
  {
    emoji: "🦉",
    title: "The Wise Old Owl",
    lines: [
      {
        emotion: "생각하는 모습",
        text: "But how could Luna send a star back up into the vast sky? She was completely stumped.",
        pronunciation:
          "벗 하우 쿠드 루나 센드 어 스타 백 업 인투 더 배스트 스카이? 쉬 워즈 컴플리틀리 스텀프트.",
      },
      {
        emotion: "아이디어 떠오름",
        text: '"Oh, of course! I should ask Grandpa Owl! He knows everything!"',
        pronunciation:
          '"오우, 오브 콜스! 아이 슈드 애스크 그랜파 아울! 히 노우즈 에브리씽!"',
      },
      {
        emotion: "존경, 공손함",
        text: "Luna carefully carried the star on her back and went to the biggest, oldest oak tree in the forest. The very wise Grandpa Owl lived there.",
        pronunciation:
          "루나 케어풀리 캐리드 더 스타 온 허 백 앤 웬트 투 더 비기스트, 올디스트 오크 트리 인 더 포레스트. 더 베리 와이즈 그랜파 아울 리브드 데어.",
      },
      {
        emotion: "낮고 온화한 목소리",
        text: '"Hooo... So the little moonlight fox asks for the sky road. You wish to send the star home?" Grandpa Owl observed Luna slowly.',
        pronunciation:
          '"후우우... 쏘 더 리틀 문라이트 폭스 애스크스 포 더 스카이 로드. 유 위시 투 센드 더 스타 홈?" 그랜파 아울 옵저브드 루나 슬로울리.',
      },
      {
        emotion: "신비로움",
        text: '"Your kindness is truly precious. Go to the peak of the tallest \'Mountain of Light.\' Make a sincere wish there, and your courage will reach the heavens."',
        pronunciation:
          '"유어 카인드니스 이즈 트루리 프레셔스. 고우 투 더 피크 오브 더 톨레스트 \'마운틴 오브 라잇\'. 메이크 어 신시어 위시 데어, 앤 유어 커리지 윌 리치 더 헤븐즈."',
      },
    ],
  },
  {
    emoji: "⛰️",
    title: "The Challenging Adventure",
    lines: [
      {
        emotion: "두려움, 떨림",
        text: "The tallest mountain... Luna had never been to such a distant and perilous place. Her legs began to tremble.",
        pronunciation:
          "더 톨레스트 마운틴... 루나 해드 네버 빈 투 서치 어 디스턴트 앤 페릴러스 플레이스. 허 레그즈 비갠 투 트렘블.",
      },
      {
        emotion: "위로, 격려",
        text: 'The shooting star glowed and whispered from Luna\'s back. "Luna, if you\'re scared, you don\'t have to go. You have already been so kind to me."',
        pronunciation:
          '더 슈팅 스타 글로우드 앤 위스퍼드 프럼 루나즈 백. "루나, 이프 유어 스케어드, 유 돈트 해브 투 고우. 유 해브 올레디 빈 쏘 카인드 투 미."',
      },
      {
        emotion: "단호함, 용기",
        text: 'But Luna shook her head resolutely. "No way! I will never give up on a friend. Let\'s go together, little star!"',
        pronunciation:
          '벗 루나 쉭 허 헤드 레졸루틀리. "노우 웨이! 아이 윌 네버 기브 업 온 어 프렌드. 레츠 고우 투게더, 리틀 스타!"',
      },
      {
        emotion: "힘든 여정",
        text: "The mountain path was far rougher than expected. The rocks were slippery, the trail was steep, and the night wind howled fiercely. Whoooosh!",
        pronunciation:
          "더 마운틴 패쓰 워즈 파 러퍼 댄 익스펙티드. 더 락스 워 슬리퍼리, 더 트레일 워즈 스팁, 앤 더 나잇 윈드 하울드 피어슬리. 후우우우쉬!",
      },
      {
        emotion: "내면의 투지",
        text: "Luna gasped for breath, but seeing the star glow warmly on her back gave her strength. 'Just a little more, just a little more!'",
        pronunciation:
          "루나 개스프트 포 브레스, 벗 씽 더 스타 글로우 워믈리 온 허 백 게이브 허 스트렝쓰. '저스트 어 리틀 모어, 저스트 어 리틀 모어!'",
      },
      {
        emotion: "응원",
        text: 'The shooting star glowed warmly and said, "Luna, you are such a brave hero! We are truly almost there!"',
        pronunciation:
          '더 슈팅 스타 글로우드 워믈리 앤 세드, "루나, 유 아 서치 어 브레이브 히어로! 위 아 트루리 올모스트 데어!"',
      },
    ],
  },
  {
    emoji: "✨",
    title: "The Magical Moment",
    lines: [
      {
        emotion: "감동, 경외",
        text: "Finally, they reached the mountain peak just before dawn. The clouds lay beneath them, and the sky was so incredibly close!",
        pronunciation:
          "파이널리, 데이 리치드 더 마운틴 피크 저스트 비포 돈. 더 클라우즈 레이 비니스 뎀, 앤 더 스카이 워즈 쏘 인크레더블리 클로우즈!",
      },
      {
        emotion: "진지함, 간절함",
        text: "Luna closed her eyes tight, cradling the shooting star in her paws, and made a wish with all her heart and sincerity.",
        pronunciation:
          "루나 클로우즈드 허 아이즈 타잇, 크레이들링 더 슈팅 스타 인 허 포즈, 앤 메이드 어 위시 윗 올 허 하트 앤 신시어리티.",
      },
      {
        emotion: "속삭이듯",
        text: '"Dear little star, please return safely to your home in the heavens. You belong up there, shining for everyone."',
        pronunciation:
          '"디어 리틀 스타, 플리즈 리턴 세이플리 투 유어 홈 인 더 헤븐즈. 유 빌롱 업 데어, 샤이닝 포 에브리원."',
      },
      {
        emotion: "마법적, 신비로움",
        text: "At that very instant, the shooting star began to glow brighter, as if to illuminate the entire world. Twinkle, twinkle, twinkle!",
        pronunciation:
          "앳 댓 베리 인스턴트, 더 슈팅 스타 비갠 투 글로우 브라이터, 애즈 이프 투 일루미네이트 디 엔타이어 월드. 트윙클, 트윙클, 트윙클!",
      },
      {
        emotion: "놀라움, 기쁨",
        text: "And slowly, so gracefully, it floated up into the sky, defying gravity. Tears welled up in Luna's eyes.",
        pronunciation:
          "앤 슬로울리, 쏘 그레이스풀리, 잇 플로우티드 업 인투 더 스카이, 디파잉 그래비티. 티어즈 웰드 업 인 루나즈 아이즈.",
      },
      {
        emotion: "아쉬움, 따뜻함",
        text: '"Luna, thank you so much! I will never forget your kindness!" the shooting star called out its final farewell.',
        pronunciation:
          '"루나, 땡큐 쏘우 머치! 아일 네버 포겟 유어 카인드니스!" 더 슈팅 스타 콜드 아웃 잇츠 파이널 페어웰.',
      },
    ],
  },
  {
    emoji: "💫",
    title: "A Special Gift",
    lines: [
      {
        emotion: "감동적",
        text: "Even as the shooting star rapidly ascended into the heavens, it sprinkled tiny, sparkling dust onto Luna as a farewell gift.",
        pronunciation:
          "이븐 애즈 더 슈팅 스타 래피들리 어센디드 인투 더 헤븐즈, 잇 스프링클드 타이니, 스파클링 더스트 온투 루나 애즈 어 페어웰 기프트.",
      },
      {
        emotion: "놀라움, 신기함",
        text: "And then, the very tip of Luna's tail began to glow softly, like a miniature galaxy!",
        pronunciation:
          "앤 덴, 더 베리 팁 오브 루나즈 테일 비갠 투 글로우 소프틀리, 라잌 어 미니어처 갤럭시!",
      },
      {
        emotion: "기쁨 폭발",
        text: '"Wow! I\'m sparkling too now! This is so amazing!" Luna wagged her tail and cheered loudly.',
        pronunciation:
          '"와우! 아임 스파클링 투 나우! 디스 이즈 쏘 어메이징!" 루나 왜그드 허 테일 앤 치얼드 라우들리.',
      },
      {
        emotion: "멀리서 들려오는 목소리",
        text: 'From far up in the sky, the star\'s warm voice echoed down. "This light is the mark of your courage! Now you are as special as the sky itself!"',
        pronunciation:
          '프럼 파 업 인 더 스카이, 더 스타즈 워름 보이스 에코드 다운. "디스 라잇 이즈 더 마크 오브 유어 커리지! 나우 유 아 애즈 스페셜 애즈 더 스카이 잇셀프!"',
      },
      {
        emotion: "벅찬 감동",
        text: "Luna gazed intently at her glowing tail, her chest swelling with emotion.",
        pronunciation:
          "루나 게이즈드 인텐틀리 앳 허 글로윙 테일, 허 체스트 스웰링 윗 이모션.",
      },
    ],
  },
  {
    emoji: "🏡",
    title: "A Warm Ending",
    lines: [
      {
        emotion: "만족스러움",
        text: "Luna walked back home to the Moonlight Forest, her radiant tail trailing behind her.",
        pronunciation:
          "루나 워크드 백 홈 투 더 문라이트 포레스트, 허 래디언트 테일 트레일링 비하인드 허.",
      },
      {
        emotion: "피곤하지만 행복함",
        text: "Her whole body was exhausted and her legs ached, but her heart was warmer and cozier than on any other day.",
        pronunciation:
          "허 홀 바디 워즈 이그져스티드 앤 허 레그즈 에익트, 벗 허 하트 워즈 워머 앤 코우지어 댄 온 애니 아더 데이.",
      },
      {
        emotion: "깨달음",
        text: "Luna realized through this adventure that helping someone unconditionally was the most valuable and shining thing one could ever do, far more than any treasure.",
        pronunciation:
          "루나 리얼라이즈드 쓰루 디스 어드벤쳐 댓 헬핑 썸원 언컨디셔널리 워즈 더 모스트 밸류어블 앤 샤이닝 씽 원 쿠드 에버 두, 파 모어 댄 애니 트레져.",
      },
      {
        emotion: "부드러운 마무리",
        text: "From that night on, Luna was no longer just an ordinary fox. All the animals in the forest respected her as a brave hero.",
        pronunciation:
          "프럼 댓 나잇 온, 루나 워즈 노우 롱거 저스트 언 오디너리 폭스. 올 더 애니멀즈 인 더 포레스트 리스펙티드 허 애즈 어 브레이브 히어로.",
      },
      {
        emotion: "따뜻한 종결",
        text: "A kind and brave little fox with a tail that glowed softly, a quiet guardian under the moonlight.",
        pronunciation:
          "어 카인드 앤 브레이브 리틀 폭스 윗 어 테일 댓 글로우드 소프틀리, 어 콰이어트 가디언 언더 더 문라이트.",
      },
      {
        emotion: "자장가 같은 엔딩",
        text: "And the countless stars in the night sky watched over Luna forever, twinkling brightly. Luna's story was passed down in the forest for a very long time. The end.",
        pronunciation:
          "앤 더 카운트리스 스타즈 인 더 나잇 스카이 와치드 오버 루나 포에버, 트윙클링 브라이틀리. 루나즈 스토리 워즈 패스드 다운 인 더 포레스트 포 어 베리 롱 타임. 디 엔드.",
      },
    ],
  },
];
