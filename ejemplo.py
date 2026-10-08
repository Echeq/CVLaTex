"""CV de ejemplo para CVLaTeX.

Devuelve diccionarios con la misma forma que ``latex_gen.datos_vacios()``
rellenos con contenido realista (en español o en chino) y sin imágenes, para
que el usuario vea cómo completar cada sección del formulario.
"""

import copy

import latex_gen


def datos_ejemplo():
    """Devuelve un CV de ejemplo listo para cargar en el formulario."""
    d = copy.deepcopy(latex_gen.datos_vacios())

    d["idioma_cv"] = "es"
    d["plantilla"] = "clasico"
    d["nombre"] = "Lucía Fernández García"
    d["profesion"] = "Desarrolladora de software backend"
    d["email"] = "lucia.fernandez@example.com"
    d["telefono"] = "+34 612 345 678"
    d["direccion"] = "Calle Mayor 24, 3.º B, 28013 Madrid"
    d["web"] = "https://luciafernandez.dev"
    d["github"] = "github.com/luciafg"
    d["linkedin"] = "linkedin.com/in/lucia-fernandez"
    d["nacimiento"] = "12/05/1996"
    d["nacionalidad"] = "Española"
    d["institucion_egresado"] = "Universidad Politécnica de Madrid"
    d["logo_egresado"] = ""

    d["datos_extra"] = [
        {"etiqueta": "Ciudad", "valor": "Madrid"},
        {"etiqueta": "Disponibilidad", "valor": "Incorporación inmediata"},
    ]

    d["perfil"] = (
        "Desarrolladora backend con seis años de experiencia diseñando APIs y "
        "servicios distribuidos en Python y Java. Especializada en arquitecturas "
        "de microservicios, bases de datos relacionales y despliegues en la nube.\n"
        "Me motiva el código limpio, la observabilidad y el trabajo en equipos con "
        "metodologías ágiles. Busco un puesto donde seguir creciendo técnicamente "
        "y aportar valor desde el primer día."
    )

    d["trabajo"] = [
        {
            "modalidad": "Híbrido",
            "puesto": "Desarrolladora Backend Senior",
            "empresa": "Fintech Nova",
            "desde": "2022",
            "hasta": "Actualidad",
            "logros": (
                "Diseñé la API de pagos con FastAPI que procesa más de dos millones "
                "de transacciones al mes.\n"
                "Reduje el tiempo de despliegue un 70 % migrando los servicios a "
                "contenedores con integración y entrega continuas.\n"
                "Mentoricé a tres desarrolladores junior y lideré la adopción de "
                "pruebas automatizadas."
            ),
            "logo": "",
        },
        {
            "modalidad": "Remoto",
            "puesto": "Desarrolladora de Software",
            "empresa": "Grupo Meridian",
            "desde": "2019",
            "hasta": "2022",
            "logros": (
                "Desarrollé servicios REST con Django para la gestión de pedidos de "
                "cuarenta franquicias.\n"
                "Optimicé consultas SQL y la caché con Redis, bajando la latencia "
                "media de 800 a 120 ms."
            ),
            "logo": "",
        },
    ]

    d["pasantia"] = [
        {
            "modalidad": "Presencial",
            "puesto": "Becaria de Desarrollo",
            "empresa": "Telecom Ibérica",
            "desde": "2018",
            "hasta": "2019",
            "logros": (
                "Colaboré en el panel interno de incidencias con Angular y Node.js.\n"
                "Automaticé los informes semanales con scripts de Python, ahorrando "
                "seis horas de trabajo."
            ),
            "logo": "",
        }
    ]

    d["proyectos"] = [
        {
            "nombre": "Rutas Sostenibles",
            "organizacion": "Hackathon Climate 2023",
            "desde": "2023",
            "hasta": "2023",
            "descripcion": (
                "Aplicación web que calcula rutas de transporte público con menor "
                "huella de carbono.\n"
                "Backend en Flask con datos abiertos GTFS y panel de estadísticas en "
                "tiempo real."
            ),
            "resultado": "Primer premio del jurado entre 42 equipos",
            "enlace": "github.com/luciafg/rutas-sostenibles",
            "logo": "",
        }
    ]

    d["proyectosu"] = [
        {
            "nombre": "Sistema de gestión de biblioteca",
            "asignatura": "Ingeniería del Software",
            "organizacion": "Universidad Politécnica de Madrid",
            "desde": "2018",
            "hasta": "2018",
            "descripcion": (
                "Aplicación de escritorio para préstamos, reservas y catálogo de una "
                "biblioteca universitaria, con base de datos PostgreSQL."
            ),
            "resultado": "Matrícula de honor",
            "enlace": "",
            "logo": "",
        }
    ]

    d["educacion"] = [
        {
            "tipo": "Máster",
            "titulo": "Máster en Ingeniería Informática",
            "institucion": "Universidad Politécnica de Madrid",
            "desde": "2018",
            "hasta": "2020",
            "nota": "9,2 / 10",
            "logo": "",
        },
        {
            "tipo": "Grado Universitario",
            "titulo": "Grado en Ingeniería del Software",
            "institucion": "Universidad de Valladolid",
            "desde": "2014",
            "hasta": "2018",
            "nota": "8,5 / 10",
            "logo": "",
        },
    ]

    d["habilidades"] = [
        {"categoria": "Lenguajes", "valores": "Python, Java, SQL, JavaScript"},
        {"categoria": "Herramientas", "valores": "Docker, Kubernetes, Git, PostgreSQL, Redis"},
    ]

    d["idiomas"] = [
        {"idioma": "Español", "nivel": "Nativo"},
        {"idioma": "Inglés", "nivel": "C1 — Advanced"},
    ]

    d["referencias"] = [
        {"nombre": "Ana Torres Ruiz", "contacto": "ana.torres@fintechnova.com — +34 600 111 222"},
    ]

    return d


def datos_ejemplo_cn():
    """Devuelve un CV de ejemplo en chino (ficción) y sin imágenes.

    Está pensado para la plantilla «chino»: los idiomas se integran como una
    categoría más de habilidades y el resto de secciones sigue el mismo
    esquema que ``datos_ejemplo()``.
    """
    d = copy.deepcopy(latex_gen.datos_vacios())

    d["idioma_cv"] = "zh"
    d["plantilla"] = "chino"
    d["nombre"] = "王小明 WANG Xiaoming"
    d["profesion"] = "软件开发实习生 / Software Development Intern"
    d["email"] = "wangxiaoming@example.com"
    d["telefono"] = "13800000000"
    d["github"] = "https://github.com/example-wxm"
    d["linkedin"] = "https://linkedin.com/in/example-wxm"
    d["nacimiento"] = "2003年5月"
    d["nacionalidad"] = "中国"
    d["institucion_egresado"] = "复旦大学"
    d["logo_egresado"] = ""
    d["datos_extra"] = []

    d["educacion"] = [
        {
            "tipo": "本科",
            "titulo": "软件工程",
            "institucion": "复旦大学",
            "desde": "2021",
            "hasta": "2025",
            "nota": "3.8 / 4.0",
            "logo": "",
        },
        {
            "tipo": "高中",
            "titulo": "理科实验班",
            "institucion": "上海中学",
            "desde": "2018",
            "hasta": "2021",
            "nota": "",
            "logo": "",
        },
    ]

    d["proyectos"] = [
        {
            "nombre": "智能课程表助手",
            "organizacion": "复旦大学计算机学院创新实践项目",
            "desde": "2023",
            "hasta": "2024",
            "descripcion": (
                "一款帮助学生自动整理课程、作业与考试安排的小程序，支持从教务"
                "系统导入课表。\n"
                "使用 Vue 3 与 FastAPI 搭建前后端，基于规则引擎识别课程冲突并"
                "给出调课建议。"
            ),
            "resultado": "获校级创新实践项目一等奖",
            "enlace": "https://github.com/example-wxm/course-planner",
            "logo": "",
        },
        {
            "nombre": "校园二手交易平台",
            "organizacion": "复旦大学开源技术社团",
            "desde": "2023",
            "hasta": "2023",
            "descripcion": (
                "面向校内同学的二手物品发布与交易网站，包含商品检索、站内消息"
                "和信用评价功能。\n"
                "使用 Spring Boot 与 MySQL 实现后端接口，部署在校园云服务器上"
                "供同学试用。\n"
                "编写接口文档并组织社团内的代码评审，项目在 GitHub 上收获 60 "
                "余颗星。"
            ),
            "resultado": "累计发布商品 800 余件，注册用户 500 余人",
            "enlace": "https://github.com/example-wxm/campus-market",
            "logo": "",
        },
    ]

    d["proyectosu"] = [
        {
            "nombre": "迷宫寻路算法可视化",
            "asignatura": "数据结构与算法",
            "organizacion": "复旦大学计算机科学技术学院",
            "desde": "2022",
            "hasta": "2022",
            "descripcion": (
                "基于 Python 与 Pygame 实现广度优先、深度优先和 A* 三种寻路"
                "算法的可视化对比。\n"
                "支持随机地图生成与逐步演示，帮助同学直观理解不同算法的效率"
                "差异。"
            ),
            "resultado": "课程设计成绩优秀（95 分）",
            "enlace": "https://github.com/example-wxm/maze-visualizer",
            "logo": "",
        },
    ]

    d["pasantia"] = [
        {
            "modalidad": "Presencial",
            "puesto": "软件开发实习生",
            "empresa": "上海云帆科技有限公司",
            "desde": "2024",
            "hasta": "2024",
            "logros": (
                "参与公司 SaaS 产品的前端模块开发，使用 Vue 3 与 TypeScript "
                "完成十余个页面组件。\n"
                "为核心模块补充自动化测试，将测试覆盖率从 62% 提升到 85%。\n"
                "整理开发文档并参与每周代码评审，获得导师「交付可靠、代码"
                "规范」的评价。"
            ),
            "logo": "",
        },
        {
            "modalidad": "Remoto",
            "puesto": "数据分析实习生",
            "empresa": "北京星河数据工作室",
            "desde": "2023",
            "hasta": "2023",
            "logros": (
                "使用 Python 与 Pandas 清洗 20 万条用户行为数据，输出周度运营"
                "分析报告。\n"
                "搭建简易指标看板，帮助团队把周报制作时间缩短一半。\n"
                "与产品经理协作梳理埋点需求，提出 3 项数据采集优化建议并被"
                "采纳。"
            ),
            "logo": "",
        },
    ]

    d["trabajo"] = []
    d["perfil"] = ""

    d["habilidades"] = [
        {"categoria": "编程语言", "valores": "Python, Java, C++, JavaScript, SQL"},
        {"categoria": "框架与工具", "valores": "Vue 3, Spring Boot, Git, Docker, Linux"},
        {"categoria": "数据分析", "valores": "Pandas, NumPy, MySQL, ECharts"},
        {"categoria": "证书与获奖", "valores": "CET-6（560 分）, 全国大学生数学建模竞赛省二等奖"},
        {"categoria": "语言", "valores": "中文（母语）, 英语（CET-6）, 西班牙语（基础）"},
    ]

    d["idiomas"] = []
    d["referencias"] = []

    return d
