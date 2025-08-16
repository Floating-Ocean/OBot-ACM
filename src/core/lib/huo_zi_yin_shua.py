"""
HuoZiYinShua code adapted from DSP_8192 at
https://github.com/DSP-8192/HuoZiYinShua/blob/main/huoZiYinShua.py
"""
import json
import os

import av
import numpy as np
import pilk
import soundfile as sf
from pypinyin import lazy_pinyin

from src.core.constants import Constants


class HuoZiYinShua:

    _TARGET_SR = 44100  # 目标采样率

    def __init__(self, lib_path: str):
        try:
            with open(os.path.join(lib_path, "dictionary.json"), encoding="utf-8") as f:
                self._single_char_dict = json.load(f)  # 非中文字符读法字典
            with open(os.path.join(lib_path, "ysddTable.json"), encoding="utf-8") as f:
                self._ost_dict = json.load(f)  # 原声大碟文件名对照

            self._pinyin_src_folder = os.path.join(lib_path, "sources")  # 单字音频文件存放目录
            self._ost_src_folder = os.path.join(lib_path, "ysddSources")  # 原声大碟音频文件存放目录

            self._ost_dict = {k.lower(): v for k, v in self._ost_dict.items()}
            # 越长片段优先级越高
            self._ost_dict = dict(sorted(self._ost_dict.items(), key=lambda x: -len(x[0])))

        except Exception as e:
            raise RuntimeError("Init HuoZiYinShua error") from e

    @classmethod
    def _load_audio(cls, target_path: str) -> np.ndarray:
        """读取音频文件"""
        data, sample_rate = sf.read(target_path)
        if len(data.shape) == 2:  # 双声道转单声道
            data = (data[:, 0] + data[:, 1]) / 2  # 左右声道相加除以2
        if sample_rate != cls._TARGET_SR:  # 统一采样率
            new_len = int((cls._TARGET_SR / sample_rate) * len(data))  # 计算转换后的长度
            data = np.interp(np.array(range(new_len)),
                             np.linspace(0, new_len - 1, len(data)), data)  # 转换
        return data

    @classmethod
    def _convert_to_pcm(cls, in_path: str, remove_origin: bool = True) -> tuple[str, int]:
        """任意媒体文件转 pcm"""
        out_path = os.path.splitext(in_path)[0] + '.pcm'
        with av.open(in_path) as in_container:
            in_stream = in_container.streams.audio[0]
            sample_rate = in_stream.codec_context.sample_rate
            with av.open(out_path, 'w', 's16le') as out_container:
                out_stream = out_container.add_stream(
                    'pcm_s16le',
                    rate=sample_rate,
                    layout='mono'
                )
                try:
                    for frame in in_container.decode(in_stream):
                        frame.pts = None
                        for packet in out_stream.encode(frame):
                            out_container.mux(packet)
                except Exception as e:
                    Constants.log.warning("[hzys] 转换 pcm 失败")
                    Constants.log.exception(e)

        if remove_origin:
            os.remove(in_path)
        return out_path, sample_rate

    @classmethod
    def _convert_to_silk(cls, media_path: str) -> str:
        """任意媒体文件转 silk, 返回silk路径"""
        pcm_path, sample_rate = cls._convert_to_pcm(media_path)
        silk_path = os.path.splitext(pcm_path)[0] + '.silk'
        pilk.encode(pcm_path, silk_path, pcm_rate=sample_rate, tencent=True)
        os.remove(pcm_path)
        return silk_path

    def generate(self, raw_data: str, output_path: str) -> str:
        """生成音频，返回 .silk 语音文件路径"""
        sf.write(output_path + '.wav', self._concat(raw_data), self._TARGET_SR)
        return self._convert_to_silk(output_path + '.wav')

    def _concat(self, raw_data: str) -> np.ndarray:
        """拼接音频"""
        concatenated = np.array([])
        missing_pinyin = []

        raw_data = raw_data.lower()  # 预处理，转为小写
        pronouns = []

        # 分割使用活字印刷的部分和使用原声大碟的部分
        split = [[raw_data, False]]  # [文本, 是否使用原声大碟]

        # 遍历要匹配的句子
        for ost in self._ost_dict.items():
            i = -1
            while i < (len(split) - 1):
                i += 1
                if split[i][1]:  # 已经被划分为原声大碟部分
                    continue
                if ost[0] in split[i][0]:  # 存在匹配
                    index_start = split[i][0].index(ost[0])  # 获取开始位置
                    # 分割
                    split.insert(i + 1, [split[i][0][index_start:index_start + len(ost[0])], True])
                    split.insert(i + 2, [split[i][0][index_start + len(ost[0]):], False])
                    split[i][0] = split[i][0][0:index_start]

        # 转换自定义的字符
        for i, word in enumerate(split):
            pronouns.append([])
            if not word[1]:  # 使用活字印刷
                pronouns[i].append("")
                for ch in word[0]:
                    if ch in self._single_char_dict:
                        # 词典中存在匹配，转换
                        pronouns[i][0] += self._single_char_dict[ch] + " "
                    else:
                        pronouns[i][0] += ch + " "  # 保持不变
                pronouns[i].append(False)  # 标记
            else:  # 使用原声大碟
                pronouns[i].append(word[0])  # 直接复制
                pronouns[i].append(True)  # 标记

        # 拼接音频
        for pronoun in pronouns:
            if not pronoun[1]:  # 使用活字印刷
                pinyin = lazy_pinyin(pronoun[0])
                for text in pinyin:  # 拆成单独的字
                    for word in text.split():  # 拼接每一个字
                        try:
                            concatenated = np.concatenate((
                                concatenated,
                                self._load_audio(os.path.join(self._pinyin_src_folder,
                                                              word + ".wav"))
                            ))
                        except Exception as e:  # 加入缺失素材列表，以空白音频代替
                            Constants.log.warning("[hzys] 加载素材失败")
                            Constants.log.exception(e)
                            if word not in missing_pinyin:
                                missing_pinyin.append(word)
                            concatenated = np.concatenate((
                                concatenated, np.zeros(int(self._TARGET_SR / 4))
                            ))

            else:  # 使用原声大碟
                try:
                    concatenated = np.concatenate((
                        concatenated,
                        self._load_audio(os.path.join(self._ost_src_folder,
                                                      self._ost_dict[pronoun[0]] + ".wav"))
                    ))
                except Exception as e:  # 加入缺失素材列表，以空白音频代替
                    Constants.log.warning("[hzys] 加载素材失败")
                    Constants.log.exception(e)
                    if self._ost_dict[pronoun[0]] not in missing_pinyin:
                        missing_pinyin.append(self._ost_dict[pronoun[0]])
                    concatenated = np.concatenate((
                        concatenated, np.zeros(int(self._TARGET_SR / 4))
                    ))

        # 如果缺失拼音，则发出警告
        if len(missing_pinyin) != 0:
            Constants.log.warning(f"[hzys] 缺失或未定义 {missing_pinyin}")

        return concatenated
