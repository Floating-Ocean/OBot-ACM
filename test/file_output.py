import os

_output_folder = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "output")
)


def get_output_path(file_name: str) -> str:
    """避免不同环境下，单元测试在相对路径里输出文件的路径不一致"""
    if not os.path.exists(_output_folder):
        os.makedirs(_output_folder)

    return os.path.join(_output_folder, file_name)
