import os

import av
import pilk

from src.core.constants import Constants


def _convert_to_pcm(in_path: str, remove_origin: bool = True) -> str:
    """任意媒体文件转 pcm"""
    out_path = os.path.splitext(in_path)[0] + '.pcm'
    converted = False
    try:
        with av.open(in_path) as in_container:
            in_stream = in_container.streams.audio[0]
            sample_rate = 24000  # 过大会导致 pc qq 无法打开
            with av.open(out_path, 'w', 's16le') as out_container:
                out_stream = out_container.add_stream(
                    'pcm_s16le',
                    rate=sample_rate,
                    layout='mono'
                )
                for frame in in_container.decode(in_stream):
                    frame.pts = None
                    for packet in out_stream.encode(frame):
                        out_container.mux(packet)
                converted = True
    except Exception as e:
        Constants.log.warning("[obot-core] 转换 pcm 失败")
        Constants.log.exception(e)

    if remove_origin and converted:
        os.remove(in_path)
    return out_path


def convert_to_silk(media_path: str) -> str:
    """任意媒体文件转 silk, 返回silk路径"""
    pcm_path = _convert_to_pcm(media_path)
    silk_path = os.path.splitext(pcm_path)[0] + '.silk'
    pilk.encode(pcm_path, silk_path, pcm_rate=24000, tencent=True)
    os.remove(pcm_path)
    return silk_path
