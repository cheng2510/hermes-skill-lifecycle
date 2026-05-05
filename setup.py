from setuptools import setup, find_packages

setup(
    name="hermes-skill-lifecycle",
    version="1.1.0",
    author="cheng2510",
    author_email="cheng2510@users.noreply.github.com",
    description="Hermes Agent 技能生命周期管理系统 — 健康评分、冲突检测、使用追踪、自动清理",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/cheng2510/hermes-skill-lifecycle",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pyyaml>=6.0",
    ],
    extras_require={
        "web": ["flask>=3.0"],
        "dev": ["pytest>=7.4", "pytest-cov>=4.1"],
    },
    entry_points={
        "console_scripts": [
            "skill-lifecycle=src.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
