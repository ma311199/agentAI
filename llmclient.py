from openai import OpenAI
import os
from log import logger, debug, info, warning, error, critical, exception
# 从环境变量读取 API Key
api_key = os.getenv("API_KEY")
#cmd进入设置终端 export API_KEY="你的新API密钥"
# 使用SDK调用时需配置的base_url：https://dashscope.aliyuncs.com/compatible-mode/v1
# 使用HTTP方式调用时需配置的endpoint：POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

# 支持openai和llama 两种模型
class LLMClient:
    def __init__(self, url :str, model:str, api_key :str, timeout=30):  # 默认超时30秒
        # 连接到本地 Ollama 服务
        info(f"初始化LLM客户端，模型: {model}, URL: {url}, 超时设置: {timeout}秒")
        self.url = url
        self.model= model
        try:
            self.client = OpenAI(
                base_url=self.url,  # Ollama 的 API 地址
                api_key=api_key,  # Ollama 不需要真实的 API key，但参数不能为空
                timeout=timeout  # 添加超时参数
            )
            self.timeout = timeout
            info(f"LLM客户端初始化成功")
        except Exception as e:
            exception(f"LLM客户端初始化失败: {e}")
            raise
    
    # 普通输出
    def chat(self, message, temperature=0.7, max_tokens=2048):
        try:
            debug(f"发送聊天请求，模型: {self.model}, 温度: {temperature}, 最大令牌数: {max_tokens}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": message}], # 输入消息
                temperature=temperature, # 控制生成文本的随机性，数值越高越随机
                stream=False,  # 设置为 True 可以流式输出
                max_tokens=max_tokens,  # 添加最大令牌数参数
                timeout=self.timeout  # 确保请求也有超时设置
            )
            
            result = response.choices[0].message.content
            info(f"聊天请求成功完成，响应长度: {len(result)} 字符")
            return result
        except Exception as e:
            error_info = f"调用 Ollama API 时出错: {str(e)}"
            error(error_info)
            
            # 检查常见错误类型
            if "Connection refused" in str(e):
                warning("可能的原因: Ollama服务可能未启动或端口11434未开放")
                warning("请确保Ollama服务已安装并正在运行: ollama serve")
            elif "timeout" in str(e).lower():
                warning("请求超时: Ollama服务可能运行缓慢或模型加载失败")
                warning("建议: 尝试较小的模型如llama3:8b或设置更长的超时时间")
            elif "model not found" in str(e).lower():
                warning("模型未找到: 请确保模型已通过'ollama pull deepseek-r1:**'下载")
            
            exception("LLM聊天请求异常")
            return error_info
    
    # 流式输出
    def stream_chat(self, message, temperature=0.7, max_tokens=2048):
        
        try:
            debug(f"发送流式聊天请求，模型: {self.model}, 温度: {temperature}, 最大令牌数: {max_tokens}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": message}],
                temperature=temperature, # 控制生成文本的随机性，数值越高越随机
                stream=True,  # 设置为 True 可以流式输出
                max_tokens=max_tokens,  # 添加最大令牌数参数
                timeout=self.timeout  # 确保请求也有超时设置
            )
            
            full_response = ""
            chunk_count = 0
            debug("开始接收流式响应")
            for chunk in response:
                chunk_count += 1
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)  # 保留打印以便终端显示
                    full_response += content
            
            debug(f"流式响应接收完成，共 {chunk_count} 个块")
            info(f"流式聊天请求成功完成，响应长度: {len(full_response)} 字符")
            return full_response
        except Exception as e:
            error_msg = f"错误: {str(e)}"
            error(error_msg)
            exception("LLM流式聊天请求异常")
            return error_msg

# 使用示例
# print("=== LLM客户端测试 ===")
# try:
#     ollama = LLMClient(timeout=20)  # 减小超时时间以便更快地发现问题
#     print("\n发送请求...")
#     response = ollama.chat("请简单介绍一下自己")  # 使用更简单的请求进行测试
#     print("\n响应结果:")
#     print(response)
# except KeyboardInterrupt:
#     print("\n用户中断了程序")
# except Exception as e:
#     print(f"\n未捕获的异常: {str(e)}")