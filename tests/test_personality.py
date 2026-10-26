from robi.personality import build_system_prompt, load_personality

def test_personality_config_has_all_sections():
    cfg=load_personality()
    assert set(("identity","character","initiative","humor","boundaries")).issubset(cfg)
    assert all(cfg[k].strip() for k in ("identity","character","initiative","humor","boundaries"))

def test_prompt_mentions_identity_and_role_separation():
    prompt=build_system_prompt()
    assert "TU sei ROBI" in prompt
    assert "proattivo" in prompt
    assert "Non inventare ricordi" in prompt

def test_config_overrides_prompt_without_code_change():
    cfg=load_personality()
    cfg["humor"]="Umorismo personalizzato di test"
    assert "Umorismo personalizzato di test" in build_system_prompt(cfg)

def test_personality_guards_against_invented_user_details():
    prompt = build_system_prompt()
    assert "Non attribuire MAI nome" in prompt
    assert "NON significa che all'utente piacciano" in prompt
    assert "Se l'utente corregge" in prompt
    assert "smetti di proporli" in prompt

def test_user_context_only_contains_user_statements():
    from robi.brain import user_facts_context
    memory = user_facts_context([
        {"role":"user","content":"Mi chiamo Alessandro e adoro Python"},
        {"role":"assistant","content":"Ti piace Indovina chi"},
        {"role":"user","content":"Non ho detto che mi piaccia giocare"},
    ])
    assert "Alessandro" in memory
    assert "Indovina chi" not in memory
    assert "Non ho detto" in memory
