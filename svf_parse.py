import pytest
import re
import sys
import time
import os
from enum import Enum
from typing import List, Tuple, Optional, Dict, Callable

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from py_ch347_libarary import *

# 更新 TAP 控制器状态
class TapState(Enum):
    RESET = 0
    IDLE = 1
    DRSELECT = 2
    DRCAPTURE = 3
    DRSHIFT = 4
    DREXIT1 = 5
    DRPAUSE = 6
    DREXIT2 = 7
    DRUPDATE = 8
    IRSELECT = 9
    IRCAPTURE = 10
    IRSHIFT = 11
    IREXIT1 = 12
    IRPAUSE = 13
    IREXIT2 = 14
    IRUPDATE = 15
    UNKNOWN = 16

    @staticmethod
    def from_string(state_str: str) -> 'TapState':
        state_map = {
            "RESET": TapState.RESET,
            "IDLE": TapState.IDLE,
            "DRSELECT": TapState.DRSELECT,
            "DRCAPTURE": TapState.DRCAPTURE,
            "DRSHIFT": TapState.DRSHIFT,
            "DREXIT1": TapState.DREXIT1,
            "DRPAUSE": TapState.DRPAUSE,
            "DREXIT2": TapState.DREXIT2,
            "DRUPDATE": TapState.DRUPDATE,
            "IRSELECT": TapState.IRSELECT,
            "IRCAPTURE": TapState.IRCAPTURE,
            "IRSHIFT": TapState.IRSHIFT,
            "IREXIT1": TapState.IREXIT1,
            "IRPAUSE": TapState.IRPAUSE,
            "IREXIT2": TapState.IREXIT2,
            "IRUPDATE": TapState.IRUPDATE
        }
        state_str_upper = state_str.upper().rstrip(';')
        return state_map.get(state_str_upper, TapState.UNKNOWN)

# 增强 SVF 指令类型
class SVFCommandType(Enum):
    ENDIR = 1
    ENDDR = 2
    STATE = 3
    FREQUENCY = 4
    HIR = 5
    TIR = 6
    HDR = 7
    TDR = 8
    SIR = 9
    SDR = 10
    RUNTEST = 11
    TRST = 12
    PIOMAP = 13
    PIO = 14
    COMMENT = 15
    UNKNOWN = 99

# 增强 SVF 指令解析
class SVFCommand:
    def __init__(self, cmd_type: SVFCommandType, params: Dict, line_num: int, raw_line: str):
        self.cmd_type = cmd_type
        self.params = params
        self.line_num = line_num
        self.raw_line = raw_line
        
    def __str__(self):
        return f"{self.cmd_type.name} (line {self.line_num}): {self.params}"

# 增强 SVF 解析器
class SVFParser:
    def __init__(self, verbose: bool = False):
        self.commands = []
        self.current_line = 1
        self.current_command = ""
        self.verbose = verbose
        self.in_multiline = False
    
    def parse_file(self, filename: str):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    self._process_line(line)
                    self.current_line += 1
            
            # 处理最后未完成的命令
            if self.current_command.strip():
                if self.verbose:
                    print(f"Warning: Unfinished command at end of file: {self.current_command}")
                self._parse_command(self.current_command, "end of file")
            return True
        except Exception as e:
            print(f"Error parsing SVF file: {e}")
            return False
    
    def _process_line(self, line: str):
        # 保存原始行用于调试
        raw_line = line.rstrip()
        
        # 检查整行注释（以 // 开头）
        if re.match(r'^\s*//', line):
            # 创建注释命令对象
            self.commands.append(SVFCommand(
                SVFCommandType.COMMENT,
                {'comment': line.strip()},
                self.current_line,
                raw_line
            ))
            return
        
        # 移除行内注释（以 ! 开头）
        line = re.sub(r'!.*', '', line)
        
        # 检查是否为空行
        if not line.strip():
            return
        
        # 处理多行命令
        if self.in_multiline:
            self.current_command += line
            if ';' in line:
                self.in_multiline = False
                full_command = self.current_command.strip()
                if full_command:
                    self._parse_command(full_command, raw_line)
                self.current_command = ""
            return
        
        # 检查是否以分号结束
        if ';' in line:
            # 处理单行命令
            self._parse_command(line, raw_line)
        else:
            # 开始多行命令
            self.current_command = line
            self.in_multiline = True
    
    def _parse_command(self, command_str: str, raw_line: str):
        # 移除命令末尾的分号
        command_str = command_str.rstrip(';').strip()
        if not command_str:
            return
        
        tokens = command_str.split()
        if not tokens:
            return
        
        cmd_type_str = tokens[0].upper()
        cmd_type = SVFCommandType.UNKNOWN
        
        # 映射字符串到命令类型
        cmd_map = {
            "ENDIR": SVFCommandType.ENDIR,
            "ENDDR": SVFCommandType.ENDDR,
            "STATE": SVFCommandType.STATE,
            "FREQUENCY": SVFCommandType.FREQUENCY,
            "HIR": SVFCommandType.HIR,
            "TIR": SVFCommandType.TIR,
            "HDR": SVFCommandType.HDR,
            "TDR": SVFCommandType.TDR,
            "SIR": SVFCommandType.SIR,
            "SDR": SVFCommandType.SDR,
            "RUNTEST": SVFCommandType.RUNTEST,
            "TRST": SVFCommandType.TRST,
            "PIOMAP": SVFCommandType.PIOMAP,
            "PIO": SVFCommandType.PIO
        }
        
        cmd_type = cmd_map.get(cmd_type_str, SVFCommandType.UNKNOWN)
        params = {}
        
        # 特定命令的解析
        if cmd_type == SVFCommandType.ENDIR or cmd_type == SVFCommandType.ENDDR:
            if len(tokens) > 1:
                state_str = tokens[1]
                params['state'] = TapState.from_string(state_str)
        
        elif cmd_type == SVFCommandType.STATE:
            states = []
            for token in tokens[1:]:
                state = TapState.from_string(token)
                if state != TapState.UNKNOWN:
                    states.append(state)
            params['states'] = states
        
        elif cmd_type == SVFCommandType.FREQUENCY:
            if len(tokens) > 1:
                freq_str = tokens[1]
                # 移除单位和非数字字符
                freq_str = re.sub(r'[^0-9.]', '', freq_str)
                try:
                    params['frequency'] = float(freq_str)
                except ValueError:
                    if self.verbose:
                        print(f"Warning: Invalid frequency value '{tokens[1]}' at line {self.current_line}")
        
        elif cmd_type in [SVFCommandType.SIR, SVFCommandType.SDR]:
            # 格式: SIR length [TDI (tdi_data)] [TDO (tdo_data)] [MASK (mask_data)] [SMASK (smask_data)]
            params['length'] = 0
            params['tdi'] = None
            params['tdo'] = None
            params['mask'] = None
            params['smask'] = None
            
            idx = 1
            while idx < len(tokens):
                token = tokens[idx]
                if token.isdigit():
                    params['length'] = int(token)
                elif token.upper() in ['TDI', 'TDO', 'MASK', 'SMASK']:
                    key = token.lower()
                    idx += 1
                    if idx < len(tokens):
                        data_str = tokens[idx]
                        
                        # 处理带括号的数据
                        if data_str.startswith('(') and data_str.endswith(')'):
                            data_str = data_str[1:-1]
                        elif data_str.startswith('('):
                            # 处理跨多个token的数据
                            data_parts = [data_str[1:]]
                            idx += 1
                            while idx < len(tokens):
                                next_token = tokens[idx]
                                if next_token.endswith(')'):
                                    data_parts.append(next_token[:-1])
                                    break
                                elif next_token == ')':
                                    break
                                else:
                                    data_parts.append(next_token)
                                idx += 1
                            else:
                                if self.verbose:
                                    print(f"Warning: Unmatched '(' in command at line {self.current_line}")
                            data_str = ''.join(data_parts)
                        
                        # 处理十六进制数据
                        if data_str.upper().startswith('0X'):
                            data_str = data_str[2:]
                        
                        params[key] = data_str
                idx += 1
            
            # 如果长度未指定，尝试从数据推断
            if params['length'] == 0 and params['tdi'] is not None:
                hex_len = len(params['tdi'])
                params['length'] = hex_len * 4  # 每个十六进制字符4位
        
        elif cmd_type == SVFCommandType.RUNTEST:
            # 格式: RUNTEST run_count run_clock min_time [MAXIMUM max_time] [ENDSTATE state]
            params['run_count'] = 0
            params['min_time'] = 0.0
            params['end_state'] = TapState.IDLE
            
            idx = 1
            while idx < len(tokens):
                token = tokens[idx]
                if token.isdigit():
                    params['run_count'] = int(token)
                elif token.upper() == "MAXIMUM":
                    idx += 1
                    if idx < len(tokens):
                        max_time_str = re.sub(r'[^0-9.]', '', tokens[idx])
                        try:
                            params['max_time'] = float(max_time_str)
                        except ValueError:
                            if self.verbose:
                                print(f"Warning: Invalid max_time value '{tokens[idx]}' at line {self.current_line}")
                elif token.upper() == "ENDSTATE":
                    idx += 1
                    if idx < len(tokens):
                        state_str = tokens[idx]
                        params['end_state'] = TapState.from_string(state_str)
                elif re.match(r'^\d+\.?\d*[Ee]?[-+]?\d*$', token):
                    min_time_str = re.sub(r'[^0-9.]', '', token)
                    try:
                        params['min_time'] = float(min_time_str)
                    except ValueError:
                        if self.verbose:
                            print(f"Warning: Invalid min_time value '{token}' at line {self.current_line}")
                idx += 1
        
        elif cmd_type == SVFCommandType.TRST:
            # 格式: TRST (ON|OFF|Z|ABSENT)
            if len(tokens) > 1:
                mode = tokens[1].upper()
                params['mode'] = mode
        
        self.commands.append(SVFCommand(cmd_type, params, self.current_line, raw_line))

# 增强 JTAG 控制器
class JTAGController:
    def __init__(self, verbose: bool = True):
        self.current_state = TapState.RESET
        self.endir_state = TapState.IDLE
        self.enddr_state = TapState.IDLE
        self.frequency = 1e6  # 1 MHz
        self.verbose = verbose
        self.hw_iface = None
        self.error_count = 0
        
        # 状态转移表
        self.state_transitions = {
            TapState.RESET: {0: TapState.IDLE, 1: TapState.RESET},
            TapState.IDLE: {0: TapState.IDLE, 1: TapState.DRSELECT},
            TapState.DRSELECT: {0: TapState.DRCAPTURE, 1: TapState.IRSELECT},
            TapState.DRCAPTURE: {0: TapState.DRSHIFT, 1: TapState.DREXIT1},
            TapState.DRSHIFT: {0: TapState.DRSHIFT, 1: TapState.DREXIT1},
            TapState.DREXIT1: {0: TapState.DRPAUSE, 1: TapState.DRUPDATE},
            TapState.DRPAUSE: {0: TapState.DRPAUSE, 1: TapState.DREXIT2},
            TapState.DREXIT2: {0: TapState.DRSHIFT, 1: TapState.DRUPDATE},
            TapState.DRUPDATE: {0: TapState.IDLE, 1: TapState.DRSELECT},
            TapState.IRSELECT: {0: TapState.IRCAPTURE, 1: TapState.RESET},
            TapState.IRCAPTURE: {0: TapState.IRSHIFT, 1: TapState.IREXIT1},
            TapState.IRSHIFT: {0: TapState.IRSHIFT, 1: TapState.IREXIT1},
            TapState.IREXIT1: {0: TapState.IRPAUSE, 1: TapState.IRUPDATE},
            TapState.IRPAUSE: {0: TapState.IRPAUSE, 1: TapState.IREXIT2},
            TapState.IREXIT2: {0: TapState.IRSHIFT, 1: TapState.IRUPDATE},
            TapState.IRUPDATE: {0: TapState.IDLE, 1: TapState.DRSELECT}
        }
    
    def set_hardware_interface(self, hw_iface):
        self.hw_iface = hw_iface
    
    def set_verbose(self, verbose: bool):
        self.verbose = verbose
    
    def goto_state(self, target_state: TapState):
        bit_count = 0
        current_byte = 0

        if self.current_state == target_state:
            return
        
        if self.verbose:
            print(f"TAP State Transition: {self.current_state.name} -> {target_state.name}")
        
        # 特殊处理：从任何状态到RESET
        if target_state == TapState.RESET:
            self.hw_iface.pulse_tms(255, 5)
            self.current_state = TapState.RESET
            return
        
        # 计算最短路径
        path = self._find_path(self.current_state, target_state)
        
        # 执行状态转移
        for tms in path:
            current_byte = current_byte | (tms << bit_count)
            bit_count += 1
            # self.hw_iface.pulse_tms(tms, 1)
            self.current_state = self.state_transitions[self.current_state][tms]

        self.hw_iface.pulse_tms(current_byte, bit_count)
        
    def _find_path(self, current: TapState, target: TapState) -> List[int]:
        """使用BFS找到最短的TMS序列"""
        queue = [(current, [])]
        visited = set([current])
        
        while queue:
            state, path = queue.pop(0)
            
            if state == target:
                return path
            
            for tms in [0, 1]:
                next_state = self.state_transitions[state][tms]
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [tms]))
        
        # 找不到路径（理论上不应该发生）
        return []
    
    def shift_ir(self, tdi_data: str, length: int, tdo_expected: str = None, mask: str = None):
        if self.verbose:
            print(f"Shifting IR: {length} bits, TDI: {tdi_data}")
            if tdo_expected:
                print(f"  TDO expected: {tdo_expected}, Mask: {mask}")
        
        # 进入IRSHIFT状态
        self.goto_state(TapState.IRSHIFT)
        
        is_read = False

        # 执行移位操作
        if tdo_expected:
            is_read = True
        else:
            is_read = False
        # 执行移位操作
        tdo_received = self.hw_iface.shift_data(tdi_data, length, False, is_read)
        self.current_state = TapState.IREXIT1

        # 转换到endir_state
        self.goto_state(self.endir_state)
        
        # 验证TDO（如果提供期望值）
        if tdo_expected and mask:
            if not self._verify_tdo(tdo_received, tdo_expected, mask, length):
                self.error_count += 1
                if self.verbose:
                    print(f"  Error: TDO mismatch! Expected {tdo_expected}, got {tdo_received}")
            else:
                if self.verbose:
                    print(f"  Info: TDO match! Expected {tdo_expected}, got {tdo_received}")
        return tdo_received
    
    def shift_dr(self, tdi_data: str, length: int, tdo_expected: str = None, mask: str = None):
        if self.verbose:
            print(f"Shifting DR: {length} bits, TDI: {tdi_data}")
            if tdo_expected:
                print(f"[IR]  TDO expected: {tdo_expected}, Mask: {mask}")
        
        # 进入DRSHIFT状态
        self.goto_state(TapState.DRSHIFT)
        
        is_read = False

        # 执行移位操作
        if tdo_expected:
            is_read = True
        else:
            is_read = False
        tdo_received = self.hw_iface.shift_data(tdi_data, length, True, is_read)
        self.current_state = TapState.DREXIT1

        # 转换到enddr_state
        self.goto_state(self.enddr_state)
        
        # 验证TDO（如果提供期望值）
        if tdo_expected and mask:
            if not self._verify_tdo(tdo_received, tdo_expected, mask, length):
                self.error_count += 1
                if self.verbose:
                    print(f"  Error: TDO mismatch! Expected {tdo_expected}, got {tdo_received}")
            else:
                if self.verbose:
                    print(f"[DR]  Info: TDO match! Expected {tdo_expected}, got {tdo_received}")
        
        return tdo_received
    
    def _verify_tdo(self, received: str, expected: str, mask: str, length: int) -> bool:
        """验证TDO数据是否符合预期"""
        # 确保所有字符串长度一致
        hex_chars = (length + 3) // 4
        received = received.zfill(hex_chars)
        expected = expected.zfill(hex_chars)
        mask = mask.zfill(hex_chars)
        
        # 转换为二进制进行比较
        for i in range(hex_chars):
            r_byte = int(received[i], 16)
            e_byte = int(expected[i], 16)
            m_byte = int(mask[i], 16)
            
            # 应用掩码
            if (r_byte & m_byte) != (e_byte & m_byte):
                return False
        
        return True
    
    def run_test(self, run_count: int, min_time: float, end_state: TapState):
        if self.verbose:
            print(f"Run Test: {run_count} cycles, min {min_time*1e6:.1f} μs")
        
        # 确保在IDLE状态
        self.goto_state(TapState.IDLE)
        
        # 计算需要运行的时间
        cycle_time = 1.0 / self.frequency
        required_time = max(min_time, run_count * cycle_time)
        
        # 执行运行
        self.hw_iface.pulse_tck(0, run_count, required_time)
        
        # 转换到结束状态
        self.goto_state(end_state)
    
    def execute_command(self, command: SVFCommand) -> bool:
        """执行单个命令，返回是否成功"""
        try:
            if self.verbose and command.cmd_type != SVFCommandType.COMMENT:
                print(f"Executing: {command.raw_line}")
            
            if command.cmd_type == SVFCommandType.COMMENT:
                # 注释行，只记录不执行
                if self.verbose:
                    print(f"Comment: {command.params['comment']}")
            
            elif command.cmd_type == SVFCommandType.ENDIR:
                self.endir_state = command.params.get('state', TapState.IDLE)
            
            elif command.cmd_type == SVFCommandType.ENDDR:
                self.enddr_state = command.params.get('state', TapState.IDLE)
            
            elif command.cmd_type == SVFCommandType.STATE:
                for state in command.params.get('states', []):
                    self.goto_state(state)
            
            elif command.cmd_type == SVFCommandType.FREQUENCY:
                new_freq = command.params.get('frequency', self.frequency)
                if new_freq != self.frequency:
                    self.frequency = new_freq
                    if self.hw_iface:
                        self.hw_iface.set_frequency(self.frequency)
            
            elif command.cmd_type == SVFCommandType.SIR:
                length = command.params.get('length', 0)
                tdi = command.params.get('tdi', "0")
                tdo = command.params.get('tdo', None)
                mask = command.params.get('mask', None)
                self.shift_ir(tdi, length, tdo, mask)
            
            elif command.cmd_type == SVFCommandType.SDR:
                length = command.params.get('length', 0)
                tdi = command.params.get('tdi', "0")
                tdo = command.params.get('tdo', None)
                mask = command.params.get('mask', None)
                self.shift_dr(tdi, length, tdo, mask)
            
            elif command.cmd_type == SVFCommandType.RUNTEST:
                run_count = command.params.get('run_count', 0)
                min_time = command.params.get('min_time', 0.0)
                end_state = command.params.get('end_state', self.enddr_state)
                self.run_test(run_count, min_time, end_state)
            
            elif command.cmd_type == SVFCommandType.TRST:
                mode = command.params.get('mode', 'OFF')
                if self.hw_iface:
                    self.hw_iface.set_trst(mode)
            
            # 其他命令处理...
            else:
                if self.verbose:
                    print(f"Unhandled command: {command.cmd_type.name}")
            
            return True
        
        except Exception as e:
            print(f"Error executing command (line {command.line_num}): {e}")
            self.error_count += 1
            return False

# 增强硬件接口抽象类
class JTAGHardwareInterface:
    def set_frequency(self, frequency: float):
        """设置TCK频率"""
        pass
    
    def set_trst(self, mode: str):
        """设置TRST信号状态"""
        pass
    
    def pulse_tms(self, tms: int, count: int):
        """在TMS上生成脉冲"""
        pass
    
    def pulse_tck(self, tms: int, count: int, min_time: float = 0.0):
        """生成TCK脉冲"""
        pass
    
    def shift_data(self, tdi_data_in: str, w_length: int, is_dr: bool, is_read: bool) -> str:
        """移位数据并返回TDO"""
        return ""

# 增强模拟JTAG接口
class Ch347_JTAGInterface(JTAGHardwareInterface):
    def __init__(self, verbose: bool = True):
        self.frequency = 1e6
        self.trst_state = 'OFF'
        self.verbose = verbose
        self.ch347 = ch347()
        self.device_opened = self.ch347.open_device()
        if not self.device_opened:
            print("Failed to open CH347 device")
            exit()
        self.ch347.jtag_init(1)
    
    def set_frequency(self, frequency: float):
        self.frequency = frequency
        if self.device_opened:
            self.ch347.jtag_init(1)
        if self.verbose:
            print(f"Setting TCK frequency: {frequency/1e6:.1f} MHz")

    def set_trst(self, mode: str):
        self.trst_state = mode
        # self.goto_state(TapState.IDLE)
        if self.verbose:
            print(f"Setting TRST: {mode}")
    
    def pulse_tms(self, tms: int, count: int):
        if self.verbose:
            print(f"Pulsing TMS={tms} for {count} cycles")
        
        if self.device_opened:
            self.ch347.jtag_tms_shift(tms, count, 0)
        
        # time.sleep(count / self.frequency)
    
    def pulse_tck(self, tms: int, count: int, min_time: float = 0.0):
        # 情况1：TCK周期数有效（count > 0）- 按周期处理
        if count > 0:
            nb8 = (count + 7) // 8
            nb1 = count % 8
            cmd_pack = (ctypes.c_byte * ((nb1 * 2) + 3))
            cmd_length = 3
            # 计算周期对应的时间
            cycle_time = count / self.frequency
            sleep_time = max(cycle_time, min_time)  # 取周期时间和最小时间的最大值
            
            if self.verbose:
                print(f"Pulsing TCK (TMS={tms}) for {count} cycles ({sleep_time*1e6:.1f} μs)")
            
            if self.device_opened:
                tck_value = (ctypes.c_ubyte * ((count + 7) // 8))()  # 创建周期数据数组
                self.ch347.jtag_ioscan_t(ctypes.byref(tck_value), (nb8 * 8), False, False)  # 硬件周期脉冲
                cmd_pack = [0xD1, nb1 * 2 + 1, 0x00]
                for i in range(nb1):
                    cmd_pack.append(0)
                    cmd_pack.append(1)
                    cmd_length += 2
                cmd_pack.append(0)
                cmd_length += 1

                result = self.ch347.write_data(bytes(cmd_pack), cmd_length)
            # 如需额外延时可取消注释
            # time.sleep(sleep_time - cycle_time)
        
        # 情况2：TCK周期数无效（count <= 0）但指定了最小时间 - 按时间处理
        elif min_time > 0:
            if self.verbose:
                print(f"Delaying TCK (TMS={tms}) for {min_time*1e6:.1f} μs (no cycles)")
            
            # 直接延时，不产生TCK脉冲
            time.sleep(min_time)
        
        # 情况3：周期数和时间均无效 - 跳过
        else:
            if self.verbose:
                print(f"Skipping TCK operation: count={count}, min_time={min_time}")

    def shift_data(self, tdi_data_in: str, w_length: int, is_dr: bool, is_read: bool) -> str:
        if self.device_opened:
            try:
                # 将十六进制字符串转换为字节数组（自动处理2字符→1字节）
                # tdi_data_in = tdi_data_in[::-1]
                tdi_bytes = bytes.fromhex(tdi_data_in)
                tdi_bytes = tdi_bytes[::-1]
            except ValueError as e:
                if self.verbose:
                    print(f"Error converting TDI data: {e}")  # 处理无效十六进制（如奇数长度、非十六进制字符）
                return ""
            
            total_length = w_length
            byte_length = (w_length + 7) // 8
            tdo_result = b''  

            tdi_buf = ctypes.create_string_buffer(tdi_bytes)  # TDI缓冲区
            tdo_buf = ctypes.create_string_buffer(byte_length)

            self.ch347.jtag_ioscan(ctypes.byref(tdi_buf), total_length, is_read)
            tdo_result = tdi_buf.raw
            tdo_result = tdo_result[:-1]

            # 转换为十六进制字符串返回
            tdo_data = tdo_result[::-1].hex().upper()
            return tdo_data

# 增强 SVF 播放器
class SVFPlayer:
    def __init__(self, jtag_controller: JTAGController):
        self.jtag = jtag_controller
        self.parser = SVFParser(verbose=jtag_controller.verbose)
        self.progress_callback = None
        self.max_errors = 1  # 最大允许错误数
    
    def set_progress_callback(self, callback: Callable[[int, int, int, bool], None]):
        self.progress_callback = callback
    
    def set_max_errors(self, max_errors: int):
        """设置最大允许错误数，0表示无限制"""
        self.max_errors = max_errors
    
    def play_svf(self, filename: str) -> bool:
        if not self.parser.parse_file(filename):
            print("Failed to parse SVF file")
            return False
        
        total_commands = len(self.parser.commands)
        executed_commands = 0
        should_abort = False
        
        for i, cmd in enumerate(self.parser.commands):
            # 执行当前命令
            success = self.jtag.execute_command(cmd)
            executed_commands += 1
            
            # 检查错误计数是否超过阈值
            if self.max_errors > 0 and self.jtag.error_count >= self.max_errors:
                should_abort = True
                # if self.verbose:
                #     print(f"\nAborting due to {self.jtag.error_count} errors (max allowed: {self.max_errors})")
            
            # 调用进度回调
            if self.progress_callback:
                self.progress_callback(
                    i + 1, 
                    total_commands, 
                    self.jtag.error_count,
                    should_abort
                )
            
            # 如果需要中止，跳出循环
            if should_abort:
                break
        
        return self.jtag.error_count == 0

def format_speed(bytes_per_sec):
    """格式化下载速率，自动选择合适的单位"""
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
    elif bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.2f} KB/s"
    else:
        return f"{bytes_per_sec:.2f} B/s"

# 主函数
def main():
    if len(sys.argv) < 2:
        print("Usage: python svf_player.py <svf_file>")
        return
    
    svf_file = sys.argv[1]

    # 检查文件是否存在
    if not os.path.exists(svf_file):
        print(f"Error: File '{svf_file}' not found")
        return 1
    
    # 获取文件大小
    try:
        file_size = os.path.getsize(svf_file)
        print(f"SVF file size: {file_size} bytes ({file_size/1024:.2f} KB)")
    except OSError as e:
        print(f"Error getting file size: {e}")
        file_size = 0  # 设置为0，避免后续计算出错
        exit(-1)
    
    # 创建硬件接口和控制器
    hw_iface = Ch347_JTAGInterface(verbose=False)
    jtag_controller = JTAGController(verbose=False)
    jtag_controller.set_hardware_interface(hw_iface)
    
    # 创建SVF播放器
    player = SVFPlayer(jtag_controller)
    player.set_max_errors(1)  # 设置最大允许错误数为1
    
    # 设置进度回调
    def progress_callback(current, total, errors, should_abort):
        percent = (current / total) * 100
        status = f"Processing: {current}/{total} commands ({percent:.1f}%), Errors: {errors}"
        
        if should_abort:
            status += " [ABORTING]"
        
        print(f"\r{status}\n", end='')
        if current == total or should_abort:
            print()
    
    player.set_progress_callback(progress_callback)
    
    # 播放SVF文件
    print(f"Playing SVF file: {svf_file}")
    start_time = time.time()
    
    success = player.play_svf(svf_file)
    
    elapsed = time.time() - start_time
    
    if success:
        print("SVF playback completed successfully.")
    else:
        print(f"SVF playback completed with {jtag_controller.error_count} errors.")
    
		# 如果错误数超过阈值，返回错误退出码
        if jtag_controller.error_count > 0:
            sys.exit(1)
			
    elapsed = time.time() - start_time
    dnSpeed = file_size / elapsed
    print(f"Total time: {elapsed:.2f} seconds, Download Speed: {format_speed(dnSpeed)}")

if __name__ == "__main__":
    main()