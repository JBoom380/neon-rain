# NEON RAIN: design spec

**NEON RAIN is a first-person noir detective shooter for phones held upright. It plays like a 1940s Hollywood noir picture set in the SkyRunner city.**

- One full case, "The Glass Saint", about 20 to 30 minutes, 4 locations.
- Mostly a shooter, with a mystery that unfolds between the gunfights.
- Scripted interrogations with readable tells (John's 2023 human-or-artificial test).
- Cigarettes are a core mechanic: focus, think, offer, and a limited pack.
- A Bogart/Bacall tone: hard-boiled voice-over, fast dialogue, a femme fatale, betrayal, a detective's code.

Next action: John reviews this spec. On approval, the implementation plan is written (writing-plans), then the grey-box slice is built.

---

## 1. Identity

| Item | Decision |
|---|---|
| Title | NEON RAIN, Case 01: "The Glass Saint" |
| Genre | First-person shooter with a noir mystery |
| Setting | The SkyRunner city (rain, smog, holo signs, hover cruisers, the PATROL cruisers overhead) with 1940s Hollywood people, clothes and talk: hats, trench coats, gloves, jazz clubs, cigarette cases |
| Tone | The Maltese Falcon, The Big Sleep, Double Indemnity, Out of the Past. Original story, characters and lines only; no quoted film dialogue |
| Platform | Phone held upright first (portrait 9:16); desktop also works |
| Hub | games.johnslagboom.com/neon-rain/ (the new repo replaces the current redirect repo JBoom380/neon-rain) |
| Content | Gore matches the wounds: blood hits, spray and wall stains from gunshots, no dismemberment. Artificial humans bleed a pale milky fluid (a visible clue). Vela is glamorous and non-explicit |

## 2. Story

**The detective:** Sam Harrow (working name), a tired private eye with a code. Narrates in hard-boiled first person.

**Characters**
1. **Vela Castellane.** The femme fatale. A singer at the Blue Orchid club. Red dress, long gloves, cigarette holder, a slow smile, quick wit (Bacall, not a vamp). She hires Harrow with a lie.
2. **Miles Corran.** Harrow's partner. Shot dead in an alley on the first night.
3. **Kastor Gale.** The fat-cat collector. Charm and menace. Wants the Glass Saint at any price.
4. **Wilmer-type gunman: "Kid" Lonnegan.** Gale's young, nervous, dangerous shooter.
5. **Lieutenant Dane.** A crooked cop who wants Harrow for Corran's murder.
6. **The bodyguard (boss).** An artificial human who guards the Saint. Fast, strong, hard to kill.

**The coveted object:** the Glass Saint, a statuette with a memory core. It holds proof of which members of the ruling families are artificial.

**Case flow**
1. **The office (prologue).** Rain on the window, light through the blinds. Vela walks in: "My sister is missing." She lights Harrow's cigarette (the smoke tutorial). That night Corran is shot. Short tutorial fight in the alley.
2. **The Blue Orchid (jazz club).** Investigate the dressing rooms, scan clues, interrogate 2 suspects. Gunfight with Gale's men in the club.
3. **The rain market.** A chase through the stalls. Gunfight. Kid Lonnegan is caught and interrogated. The key clue: the bullet that killed Corran.
4. **Gale's penthouse.** Interrogate Gale. Vela's own interrogation (her meters read too calm). Gunfight. The Saint is found to be a fake.
5. **The docks at dawn (finale).** Boss fight with the artificial bodyguard in the storm. Then the accusation.

**Twist:** Vela killed Corran. She used Harrow to find the real Saint.

**Endings (from the accusation)**
1. Turn her in (the code). Best case score. "When a man's partner is killed, he's supposed to do something about it" is the spirit; the line itself is written fresh.
2. Let her go. Bittersweet ending, lower score.
3. Accuse the wrong person. Case failed; Dane arrests Harrow.

## 3. Play systems

1. **Movement and aim.** First person, smooth camera, light aim assist on phones.
2. **Weapons.** A detective revolver: 6 shots, heavy recoil, head shots do double damage, fast reload with a cylinder spin. A shock baton for close range.
3. **Enemies.**
   - Gale's men: suits and hats, take cover, flank.
   - Street thugs: rush with knives and flashlights.
   - Kid Lonnegan: a mini-boss in the market.
   - The artificial bodyguard: the final boss; dodges, charges, takes many hits.
4. **Health.** No health bar. The screen edges darken red; recover in cover; 3 lives per scene.
5. **SCAN.** Hold to make clues glow amber; each clue writes a note in the case file.
6. **Case file.** Clues, suspects, notes; open at any time.
7. **Interrogation.**
   - A painted close-up portrait with 3 expressions.
   - Choose 4 of 8 questions.
   - Pulse, eye and hesitation meters react to each answer.
   - Slips in answers show only if the matching clue was found.
   - Verdict: HUMAN or ARTIFICIAL, and later the accusation.
8. **Cigarettes (different from Freebird).**
   - **Focus (combat):** hold SMOKE for a drag; time slows to 40% for 3 s and the aim steadies.
   - **Think (detective):** smoking while scanning shows deeper clue notes and links between clues.
   - **Offer (interrogation):** give a suspect a smoke. A human relaxes (pulse drops, lies stand out). An artificial human takes it but never inhales (a tell).
   - **Pack:** start with 6; find more in ashtrays, on bar counters and on guards. Each use costs one.
   - Lighting her cigarette, or her lighting his, is a scene beat in dialogue.
   - Optional (off unless John asks): lighter flame shows drafts to hidden doors; 3 drags in a row cause a cough that gives away the player's position.
9. **Scoring.** Accusation correct, clues found, shooting accuracy, time, cigarettes left.

## 4. Controls (phone, upright)

- Left thumb: floating move stick.
- Right thumb: drag to look and aim.
- FIRE: a trigger button just above the left stick, pressed with the left index finger.
- Right side: RELOAD, SCAN, SMOKE, INTERACT.
- Desktop: WASD + mouse look, left click fire, R reload, F scan, E interact, Q smoke.

## 5. Look and sound

- **Render:** three.js, low-res pixel pass with the SkyRunner film palette (smog, sodium amber, teal, dull red), rain, fog, hard light through blinds, deep shadows.
- **Optional film mode:** black and white with one colour kept: red (Vela's lipstick and dress, blood).
- **Art (ComfyUI, when restarted):** 6 character portraits with 3 expressions each, Vela full-figure sprites, the title art, the case file art.
- **Voice-over:** Harrow's narration through John's voice pipeline (E:\claude\Projects\TheLastKeeper\voice\: Kokoro reference, WORLD shaping, Chatterbox clone, Whisper QC), a low gravelly voice. Other characters: dialogue text first; voices later if John wants them.
- **Music:** new Suno tracks by John. Prompts:
  1. Title / case file: "slow neo-noir synth, lonely saxophone, rain, 1982 film score, Vangelis-style pads, 70 bpm, instrumental"
  2. Investigation: "ambient detective synth, low drones, soft pulses, ticking, rain on glass, tense and quiet, instrumental"
  3. Interrogation: "minimal tension underscore, heartbeat bass, sparse piano notes, cold synth, slow, instrumental"
  4. Gunfight: "dark synthwave action, driving bass, heavy drums, distorted synth stabs, 120 bpm, instrumental"
  5. Boss at the docks: "epic noir synth climax, storm, choir pads, pounding drums, rising tension, instrumental"
  6. Ending: "melancholic sax and synth, rain fading out, bittersweet, instrumental"
  7. Vela's theme: "sultry noir lounge, slow saxophone, brushed drums, female vocalise, smoky"
  Placeholders play until the tracks arrive.

## 6. Build

- **Folder:** C:\Users\John\Documents\GitHub\projects\neon-rain-fps\ (repo JBoom380/neon-rain, replacing the redirect when published).
- **Method:** the SkyRunner/Bum Rush method: `src/SPEC.md` contract, a core loop, modules on a global namespace, an event bus, `build.py` inlines to one `index.html`, assets as files.
- **Reuse from SkyRunner:** the palette pass, rain and fog, the floating stick, the TAP TO ENTER music gate, the link-preview tags.
- **Builders (parallel, Opus):** core + FPS camera; controls; weapons + gore; enemy AI; levels (office, club, market, penthouse, docks); clues + SCAN + case file; interrogation + portraits + dialogue; UI + audio + cigarettes.
- **Order:**
  1. Grey-box slice: the office prologue and the club (one fight, one interrogation, the smoke mechanics). John tests on his phone.
  2. The full case: market, penthouse, docks, endings.
  3. Art pass (ComfyUI portraits and title), voice-over, John's Suno tracks.
- **Tests:** Playwright on a 390x844 touch screen; the whole case played through by script; fps >= 55; zero console errors; screenshot contact sheets reviewed by eye and sent to John.
- **Publishing:** only on John's "push".

## 7. Legal

Original names, story and lines only. No film titles, character names or quoted dialogue from any film. No real brands.

## 8. Story lock (2026-10-07, supersedes section 2 where they differ)

- **Vela Castellane** (lead, the blonde: art\vela_favorites\FAV1_blonde_seed52.png): Kastor Gale's 24-year-old trophy wife; hires Harrow with a lie ("my sister is missing"); secretly Corran's lover; killed Corran out of jealousy when he fell for Dolores and planned to take the Saint; plans a Double Indemnity trap on Gale.
- **Dolores Delacroix** (the raven: art\vela_favorites\FAV2_raven_seed61.png): Blue Orchid singer, Gale's discarded mistress, hates Vela, stole the Saint to escape. Cyber twist: she is the artificial copy of Gale's dead first wife and does not know it.
- **Iris Corran**: Miles's wife; sleeps with Harrow; bought her husband's memories of Vela from a memory broker.
- **The Glass Saint**: in the cyber layer, a memory core holding Gale's dead first wife's mind; the one found at the docks is wiped (the fake).
- **Harrow**: has a 40-minute memory gap the night Corran died (bought a wipe); the finale proves he was there but did not fire.
- Ending: Vela says she loves him; he turns her in (the code); Dolores walks into the rain with her secret.
