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
