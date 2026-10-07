// NEON RAIN story data for the grey-box slice: Case 01 "The Glass Saint", prologue + the Blue Orchid.
// Original names, story and lines only. VO = Harrow's voice-over.
(function () {
  const H = 'HARROW', VO = 'HARROW (V.O.)', V = 'VELA', D = 'DOLORES';
  NR.story = {
    office: {
      card: 'THE CITY.\nTHE RAIN.\nTHE THIRD NIGHT OF IT.',
      open: [
        [VO, 'The rain had been at my window for three days. It wanted in. So did everybody else.'],
        [VO, 'Miles went home at six. I stayed with a bottle and the bills. The bills were winning.'],
      ],
      enter: [
        [VO, 'Then the door opened, and the rest of the night stopped being mine.'],
      ],
      talk: [
        [VO, 'Blonde. Red to the knee, black to the elbow. She stood in my doorway like she had paid for it.'],
        [V, 'Mr. Harrow? The glass on your door says you find things.'],
        [H, 'The glass says a lot of things. Most of it I paid a sign painter to say.'],
        [V, 'My sister is missing. Four days now. The police say girls go missing in this city the way umbrellas do.'],
        [H, 'The police like a short list. What do they call her?'],
        [V, 'Dolores. She sings at the Blue Orchid. Or she did, until Thursday.'],
        [VO, 'She said "sister" the way a card sharp says "fair deal". I let it go. Her money had no lies in it.'],
        [V, 'You look like a man who needs a light more than a client.'],
      ],
      light: [
        [VO, 'She lit mine before her own. Some women always go first. They like to see where the fire goes.'],
      ],
      smokeTut: { title: 'CIGARETTES', body: 'SMOKE costs one cigarette.\n\nIN A FIGHT: FOCUS. Time slows to 40% for 3 s and your aim steadies.\n\nWHILE YOU SCAN: THINK. Harrow writes deeper notes on each clue.\n\nIN QUESTIONING: OFFER one. Watch what they do with it.\n\nYou carry a pack of 6. Find more on bars, in ashtrays and on the men you drop.' },
      after: [
        [H, 'Two hundred, up front. Expenses if I bleed.'],
        [V, 'Find her before anyone else does, Mr. Harrow. Anyone at all.'],
      ],
      leave: [
        [VO, 'She left the money and her perfume. Only one of them would last the week.'],
      ],
      gunTut: { title: 'THE REVOLVER', body: 'Six shots. RELOAD when the cylinder runs dry.\n\nHold your phone upright. The left thumb moves. Drag the right side to aim. FIRE sits just above the stick.\n\nHead shots do double damage. Cover lets you get your breath back.' },
    },
    alley: {
      card: 'THAT NIGHT.\nTHE ALLEY BEHIND KESTREL STREET.',
      open: [
        [VO, 'Miles called at midnight. He said he had a lead on the girl. He said the alley behind Kestrel Street.'],
        [VO, 'By the time I got there, the lead had friends.'],
      ],
      fight: [[VO, 'Three of them. Two with knives, one with a gun and no manners.']],
      clear: [[VO, 'The rain washed them toward the drain. It had a lot of practice.']],
      body: [
        [VO, 'Miles Corran. Eight years my partner. Somebody put him down in the rain and did not wait to watch.'],
        [VO, 'There was a Blue Orchid matchbook in his fist. Miles never smoked.'],
        [VO, 'There were forty minutes of that night I could not account for. I told myself it was the rain.'],
      ],
      matchNote: 'Blue Orchid matchbook, in Miles\'s fist. He never smoked. He wanted me to find it.',
    },
    club: {
      card: 'THE BLUE ORCHID.\nONE IN THE MORNING.',
      open: [
        [VO, 'The Blue Orchid. The band played like it owed money. Every booth had a candle and a secret, and the candles were cheaper.'],
        [VO, 'If Dolores was missing, she was missing in plain sight.'],
      ],
      scanTut: { title: 'SCAN', body: 'Hold SCAN. Clues glow amber.\n\nKeep a glowing clue under your sights to read it. Each one goes in the CASE FILE.\n\nSmoke while you scan and Harrow will THINK: deeper notes, and links between clues.' },
      notYet: [[D, 'You have the look of a man with questions and nothing to hang them on. Come back when you do.']],
      meet: [
        [VO, 'She had a face the camera would forgive anything. I was not the camera.'],
        [D, 'You are not a fan. Fans bring flowers.'],
        [H, 'I bring questions. They keep longer.'],
      ],
      interroTut: { title: 'QUESTIONING', body: 'Ask 4 of 8 questions.\n\nWatch the meters. A frightened human\'s pulse climbs when a question cuts close, and drops with a smoke. Eyes dart. Answers wait.\n\nClues you found open new questions and draw out slips.\n\nThen decide: HUMAN or ARTIFICIAL.' },
      afterVerdict: {
        ARTIFICIAL: [[VO, 'Her pulse never moved. Not once. Either she was the coolest liar in the city, or someone built her not to need to lie.']],
        HUMAN: [[VO, 'She was frightened, and frightened is human. I wrote it down and hoped I could read my own hand later.']],
      },
      warn: [
        [D, 'Go out the back, detective. Kastor\'s boys do not knock, and they do not tip.'],
        [VO, 'She was right about the knocking.'],
      ],
      clear: [
        [VO, 'One of them bled like spilled milk. Pale and slow.'],
        [VO, 'Somebody in this city was building people. Somebody else was buying them. And my client had lied to me twice before breakfast.'],
      ],
    },
    clues: {
      holder: { name: 'Holder tip, booth three', note: 'A cigarette-holder tip in the ashtray of booth three. Fresh lipstick on it, a bright red.', think: 'The same red my client wore. She said she never sets foot in this club. The ashtray says otherwise. Link: Vela was here, with someone who sat in booth three.' },
      ticket: { name: 'Ferry ticket', note: 'A night-ferry ticket in the dressing room. One way, paid in cash, for tomorrow night.', think: 'Nobody buys one way for a holiday. Dolores is not missing. She is leaving, and she is afraid of who will notice.' },
      mirror: { name: 'Cracked mirror', note: 'A cracked dressing-room mirror. On one shard, a smear of something pale and milky.', think: 'Not blood. Too pale, too slow. I saw that colour once on the floor of a lab on the hill. They do not make people there. They make copies.' },
    },
    dolores: {
      name: 'DOLORES DELACROIX', role: 'Singer, the Blue Orchid',
      artificial: true,
      offer: { mood: 'warm', pulse: 62, eye: 0.15, hes: 0.3, a: 'Thank you, detective. You are sweeter than you look.', vo: 'She held it like a prop. The ember burned down to her glove. She never drew on it once.', note: 'Offered a smoke. She took it and never inhaled.' },
      questions: [
        { id: 'sister', q: 'A woman hired me to find you. She says she is your sister.', a: 'Then she is a liar or a stranger. I do not have a sister. I do not have much of anything.', mood: 'guarded', pulse: 62, eye: 0.15, hes: 0.4 },
        { id: 'night', q: 'Where were you last night at midnight?', a: 'Right here. Second show. Two hundred people watched me, and not one of them listened.', mood: 'warm', pulse: 61, eye: 0.1, hes: 0.3 },
        { id: 'miles', q: 'Miles Corran. You know him?', a: 'He liked the late set. He tipped well and talked less.', mood: 'guarded', pulse: 62, eye: 0.2, hes: 0.6, slip: { clue: 'holder', text: 'He sat in booth three. Not alone. A blonde, the kind who never comes here.' } },
        { id: 'gale', q: 'What is Kastor Gale to you?', a: 'He owns the club, the band and my contract. He used to own more.', mood: 'cold', pulse: 63, eye: 0.2, hes: 0.5 },
        { id: 'saint', q: 'Ever hear of the Glass Saint?', a: 'A saint made of glass? Say a prayer to it and see what it hears.', mood: 'cold', pulse: 61, eye: 0.25, hes: 1.1 },
        { id: 'leaving', q: 'Going somewhere, Dolores?', a: 'A girl can buy a ticket. It is still a free city, mostly.', mood: 'guarded', pulse: 62, eye: 0.2, hes: 0.7, slip: { clue: 'ticket', text: 'Tomorrow night. The ferry. One way, so do not ask me to write.' } },
        { id: 'hand', q: 'How long have you sung at the Orchid?', a: 'Since I can remember. Funny. I cannot remember much before it.', mood: 'guarded', pulse: 61, eye: 0.5, hes: 1.8,
          clueQ: { clue: 'mirror', q: 'You cut your hand on that mirror.', a: 'I broke it. Seven years of bad luck.', slip: 'It does not hurt. It never does.', mood: 'cold', pulse: 61, eye: 0.3, hes: 1.4 } },
        { id: 'mother', q: 'Tell me about your mother.', a: 'My mother... She kept a garden. Roses, I think. Or I saw it in a picture once. Why does it matter?', mood: 'warm', pulse: 62, eye: 0.75, hes: 2.4 },
      ],
    },
    end: { title: 'END OF THE SLICE', sub: 'CASE 01: THE GLASS SAINT\ncontinues in the rain market' },
  };
})();
