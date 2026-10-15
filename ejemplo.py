"""Sample CVs for CVLaTeX.

Return dicts with the same shape as ``latex_gen.empty_data()`` filled with
realistic content (in Spanish or Chinese) and without images, so the user
sees how to complete each form section.
"""

import copy

import latex_gen


def sample_data():
    """Return a sample CV ready to load into the form."""
    d = copy.deepcopy(latex_gen.empty_data())

    d["cv_language"] = "es"
    d["template"] = "classic"
    d["name"] = "Lucía Fernández García"
    d["profession"] = "Desarrolladora de software backend"
    d["email"] = "lucia.fernandez@example.com"
    d["phone"] = "+34 612 345 678"
    d["address"] = "Calle Mayor 24, 3.º B, 28013 Madrid"
    d["socials"] = [
        {"network": "github", "label": "", "value": "github.com/luciafg"},
        {"network": "linkedin", "label": "", "value": "linkedin.com/in/lucia-fernandez"},
        {"network": "website", "label": "", "value": "https://luciafernandez.dev"},
    ]
    d["school_name"] = "Universidad Politécnica de Madrid"
    d["school_logo"] = ""

    d["extra_fields"] = [
        {"label": "Nacimiento", "value": "12/05/1996"},
        {"label": "Nacionalidad", "value": "Española"},
    ]

    d["summary"] = (
        "Desarrolladora backend con seis años de experiencia en Python y Java. "
        "Especializada en APIs, microservicios y despliegues en la nube."
    )

    d["work"] = [
        {
            "work_mode": "hybrid",
            "position": "Desarrolladora Backend Senior",
            "company": "Fintech Nova",
            "start": "2022",
            "end": "Actualidad",
            "achievements": (
                "Diseñé la API de pagos con FastAPI para más de dos millones de "
                "transacciones al mes.\n"
                "Mentoricé a tres desarrolladores junior y promoví las pruebas "
                "automatizadas."
            ),
            "logo": "",
        },
    ]

    d["internships"] = [
        {
            "work_mode": "onsite",
            "position": "Becaria de Desarrollo",
            "company": "Telecom Ibérica",
            "start": "2018",
            "end": "2019",
            "achievements": (
                "Automaticé los informes semanales con scripts de Python, ahorrando "
                "seis horas de trabajo."
            ),
            "logo": "",
        }
    ]

    d["projects"] = [
        {
            "name": "Rutas Sostenibles",
            "organization": "Hackathon Climate 2023",
            "start": "2023",
            "end": "2023",
            "description": (
                "Aplicación web que calcula rutas de transporte público con menor "
                "huella de carbono.\n"
                "Backend en Flask con datos abiertos GTFS y panel de estadísticas."
            ),
            "result": "Primer premio del jurado entre 42 equipos",
            "link": "github.com/luciafg/rutas-sostenibles",
            "logo": "",
        }
    ]

    d["university_projects"] = [
        {
            "name": "Sistema de gestión de biblioteca",
            "course": "Ingeniería del Software",
            "organization": "Universidad Politécnica de Madrid",
            "start": "2018",
            "end": "2018",
            "description": (
                "Aplicación de escritorio para préstamos, reservas y catálogo, con "
                "base de datos PostgreSQL."
            ),
            "result": "Matrícula de honor",
            "link": "",
            "logo": "",
        }
    ]

    d["education"] = [
        {
            "degree_type": "master",
            "degree": "Máster en Ingeniería Informática",
            "institution": "Universidad Politécnica de Madrid",
            "start": "2018",
            "end": "2020",
            "grade": "9,2 / 10",
            "logo": "",
        },
        {
            "degree_type": "bachelor",
            "degree": "Grado en Ingeniería del Software",
            "institution": "Universidad de Valladolid",
            "start": "2014",
            "end": "2018",
            "grade": "8,5 / 10",
            "logo": "",
        },
    ]

    d["skills"] = [
        {"category": "Lenguajes", "values": "Python, Java, SQL"},
        {"category": "Herramientas", "values": "Docker, Git, PostgreSQL"},
    ]

    d["languages"] = [
        {"language": "Español", "level": "Nativo"},
        {"language": "Inglés", "level": "C1 — Advanced"},
    ]

    d["references"] = [
        {"name": "Ana Torres Ruiz", "contact": "ana.torres@fintechnova.com"},
    ]

    return d


def sample_data_zh():
    """Return a sample CV in Chinese (fiction) and without images.

    It is meant for the "chinese" template: the languages are integrated as one
    more skills category and the remaining sections follow the same schema as
    ``sample_data()``.
    """
    d = copy.deepcopy(latex_gen.empty_data())

    d["cv_language"] = "zh"
    d["template"] = "chinese"
    d["name"] = "王小明 WANG Xiaoming"
    d["profession"] = "软件开发实习生 / Software Development Intern"
    d["email"] = "wangxiaoming@example.com"
    d["phone"] = "13800000000"
    d["socials"] = [
        {"network": "github", "label": "", "value": "https://github.com/example-wxm"},
        {"network": "linkedin", "label": "", "value": "https://linkedin.com/in/example-wxm"},
    ]
    d["school_name"] = "复旦大学"
    d["school_logo"] = ""
    d["extra_fields"] = [
        {"label": "出生年月", "value": "2003年5月"},
        {"label": "国籍", "value": "中国"},
    ]

    d["education"] = [
        {
            "degree_type": "bachelor",
            "degree": "软件工程",
            "institution": "复旦大学",
            "start": "2021",
            "end": "2025",
            "grade": "3.8 / 4.0",
            "logo": "",
        },
        {
            "degree_type": "high_school",
            "degree": "理科实验班",
            "institution": "上海中学",
            "start": "2018",
            "end": "2021",
            "grade": "",
            "logo": "",
        },
    ]

    d["projects"] = [
        {
            "name": "智能课程表助手",
            "organization": "复旦大学计算机学院创新实践项目",
            "start": "2023",
            "end": "2024",
            "description": (
                "一款帮助学生自动整理课程、作业与考试安排的小程序，支持从教务"
                "系统导入课表。\n"
                "使用 Vue 3 与 FastAPI 搭建前后端，基于规则引擎识别课程冲突并"
                "给出调课建议。"
            ),
            "result": "获校级创新实践项目一等奖",
            "link": "https://github.com/example-wxm/course-planner",
            "logo": "",
        },
        {
            "name": "校园二手交易平台",
            "organization": "复旦大学开源技术社团",
            "start": "2023",
            "end": "2023",
            "description": (
                "面向校内同学的二手物品发布与交易网站，包含商品检索、站内消息"
                "和信用评价功能。\n"
                "使用 Spring Boot 与 MySQL 实现后端接口，部署在校园云服务器上"
                "供同学试用。\n"
                "编写接口文档并组织社团内的代码评审，项目在 GitHub 上收获 60 "
                "余颗星。"
            ),
            "result": "累计发布商品 800 余件，注册用户 500 余人",
            "link": "https://github.com/example-wxm/campus-market",
            "logo": "",
        },
    ]

    d["university_projects"] = [
        {
            "name": "迷宫寻路算法可视化",
            "course": "数据结构与算法",
            "organization": "复旦大学计算机科学技术学院",
            "start": "2022",
            "end": "2022",
            "description": (
                "基于 Python 与 Pygame 实现广度优先、深度优先和 A* 三种寻路"
                "算法的可视化对比。\n"
                "支持随机地图生成与逐步演示，帮助同学直观理解不同算法的效率"
                "差异。"
            ),
            "result": "课程设计成绩优秀（95 分）",
            "link": "https://github.com/example-wxm/maze-visualizer",
            "logo": "",
        },
    ]

    d["internships"] = [
        {
            "work_mode": "onsite",
            "position": "软件开发实习生",
            "company": "上海云帆科技有限公司",
            "start": "2024",
            "end": "2024",
            "achievements": (
                "参与公司 SaaS 产品的前端模块开发，使用 Vue 3 与 TypeScript "
                "完成十余个页面组件。\n"
                "为核心模块补充自动化测试，将测试覆盖率从 62% 提升到 85%。\n"
                "整理开发文档并参与每周代码评审，获得导师「交付可靠、代码"
                "规范」的评价。"
            ),
            "logo": "",
        },
        {
            "work_mode": "remote",
            "position": "数据分析实习生",
            "company": "北京星河数据工作室",
            "start": "2023",
            "end": "2023",
            "achievements": (
                "使用 Python 与 Pandas 清洗 20 万条用户行为数据，输出周度运营"
                "分析报告。\n"
                "搭建简易指标看板，帮助团队把周报制作时间缩短一半。\n"
                "与产品经理协作梳理埋点需求，提出 3 项数据采集优化建议并被"
                "采纳。"
            ),
            "logo": "",
        },
    ]

    d["work"] = []
    d["summary"] = ""

    d["skills"] = [
        {"category": "编程语言", "values": "Python, Java, C++, JavaScript, SQL"},
        {"category": "框架与工具", "values": "Vue 3, Spring Boot, Git, Docker, Linux"},
        {"category": "数据分析", "values": "Pandas, NumPy, MySQL, ECharts"},
        {"category": "证书与获奖", "values": "CET-6（560 分）, 全国大学生数学建模竞赛省二等奖"},
        {"category": "语言", "values": "中文（母语）, 英语（CET-6）, 西班牙语（基础）"},
    ]

    d["languages"] = []
    d["references"] = []

    return d
