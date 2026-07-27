O projeto terá os seguintes arquivos arquivos:
    

'_APP_UI_' = pasta:
    Todas as janelas e logica da interface gráfica.
    
    
'_APPDATA_' = pasta:
    Aqui ira ter os scripts e logica para criação de tudo que precisar para cerebro do projeto,
    esse modulo ira criar arquivos e manipulalos, backup etc... em ...AppData\Roaming\projeto
    'Atenção todos os logs serao reecriados a cada nova sessão'    

    
'_CONFIGURA_' = pasta:
    Aqui será respnsavel por configurações em gerais, tipo jsons e seus scripts de gerenciadores etc..
    Em seu __init__.py ira ficar todos e qualquer hardcodes ou seja nenhum outro lugar pode ter cores
    ou atalhos fixos etc... tudo tem que ficar e ser puxado daqui!
    
    
'_LOGS_' = pasta:
    Esse modulo sera respnsavel por todos os logs do projeto enquanto estiver sandbox, os seguintes logs:
        
        "Exception.log"
        "Fulthandler.log"
        "Crash.log"
    
        
'_ULTILIDADES_' = pasta:
    Scripts e logicas para ferramentas , imagens poupaps menus icones etc...
    
                 
'main.py' = arquivo:
    Este arquivo sera apenas para chamadas dos logs de entrada e encerramentos, chamada a     interface '_APP_UI_'.
    exemplo:   
    from _LOG_.log import log
    from _CONFIGURA_ import TEMA_QT_PADRAO, PASTA_APPDATA
        
    _crash_log = os.path.join(PASTA_APPDATA, "Crash.log")
    _crash_dump_path = os.path.join(PASTA_APPDATA, "Fulthandler.log")    
    _exc_log_path = os.path.join(PASTA_APPDATA, "Exception.log")
    log.erro("main.py", "excepthook", f"CRASH NAO TRATADO:\n{texto}")
