#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有可用模型的调用功能

基于 super_simple.py 的代码，测试多个不同的AI模型
"""

import requests
import hashlib
import time
from typing import Dict, List, Tuple

# 配置
API_KEY = "crqGkYW3wbYMQ9P"

# 所有可用模型配置
models = [
    {"name": "gpt-5", "model_key": "model-20250811154752-vr0n93", "api_type": "medlive"},
    {"name": "gpt-5-mini", "model_key": "model-20250811155252-mkp4f1", "api_type": "medlive"},
    {"name": "gpt-5-nano", "model_key": "model-20250811155549-lbti28", "api_type": "medlive"},
    {"name": "gpt-4o", "model_key": "model-20240514102053-gji2rl", "api_type": "medlive"},
    {"name": "Doubao-1.5-pro-32k-250115", "model_key": "model-20250318181721-b32508", "api_type": "medlive"},
    {"name": "qwen-max", "model_key": "model-20250402153605-83nj1j", "api_type": "medlive"},
    {"name": "qwen-plus", "model_key": "model-20250409160656-e21bf1", "api_type": "medlive"},
    {"name": "qwen3-32b", "model_key": "model-20250623150216-vr23n0", "api_type": "medlive"},
    {"name": "DeepSeek-V3-250324", "model_key": "model-20250411145303-8pnzvw", "api_type": "medlive"},
    {"name": "DeepSeek-R1-250528", "model_key": "model-20250530110729-fj0rk3", "api_type": "medlive"},
    {"name": "deepseek-reasoner", "model_key": "deepseek-reasoner", "api_type": "deepseek"}
]

def call_ai_model(question: str, model_key: str, model_name: str, api_type: str = "medlive") -> Tuple[bool, str, float]:
    """调用指定的AI模型
    
    Args:
        question: 问题文本
        model_key: 模型的key
        model_name: 模型名称
        api_type: API类型 ("medlive" 或 "deepseek")
        
    Returns:
        (是否成功, 响应内容, 响应时间)
    """
    if api_type == "deepseek":
        return call_deepseek_api(question, model_key)
    else:
        return call_medlive_api(question, model_key)

def call_medlive_api(question: str, model_key: str) -> Tuple[bool, str, float]:
    """调用MedLive API"""
    start_time = time.time()
    
    try:
        timestamp = int(time.time())
        
        # 构建token参数
        params = {
            "project_id": "131",
            "timestamp": str(timestamp),
            "user_id": "3790046"
        }
        
        # 按键名排序并拼接
        sorted_keys = sorted(params.keys())
        raw = ''.join(f"{k}{params[k]}" for k in sorted_keys)
        
        # 生成token（两次MD5）
        inner = hashlib.md5(raw.encode()).hexdigest()
        token = hashlib.md5((inner + API_KEY).encode()).hexdigest().upper()
        
        url = "https://chat001.medlive.cn/api/project/chat"
        data = {
            "project_id": 131,
            "timestamp": timestamp,
            "user_id": "3790046",
            "question": question,
            "chat_id": "",
            "stream": 0,
            "model_key": model_key
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(url, data=data, headers=headers, timeout=60)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') is True:
                answer = result.get('data', {}).get('answer', '')
                if answer:
                    return True, answer, response_time
                else:
                    return False, "API返回了空回答", response_time
            else:
                return False, f"API返回错误: {result.get('message', '未知错误')}", response_time
        else:
            return False, f"HTTP错误: {response.status_code}", response_time
            
    except Exception as e:
        response_time = time.time() - start_time
        return False, f"请求异常: {str(e)}", response_time

def call_deepseek_api(question: str, model_key: str) -> Tuple[bool, str, float]:
    """调用DeepSeek官网API"""
    api_key = "sk-5f54aec15d4040469f3856c404b2b177"
    
    try:
        start_time = time.time()
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model_key,
            "messages": [
                {"role": "user", "content": question}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if answer:
                return True, answer, response_time
            else:
                return False, "API返回了空回答", response_time
        else:
            return False, f"HTTP错误: {response.status_code} - {response.text}", response_time
            
    except requests.exceptions.Timeout:
        return False, "连接超时(60s)", 60
    except Exception as e:
        return False, f"请求异常: {str(e)}", 0

def test_single_model(model_name: str, model_key: str, api_type: str = "medlive", question: str = "你好，请简单介绍一下你自己") -> Dict:
    """测试单个模型
    
    Args:
        model_name: 模型名称
        model_key: 模型key
        api_type: API类型
        question: 测试问题
        
    Returns:
        测试结果字典
    """
    print(f"\n🔍 测试模型: {model_name} ({api_type} API)")
    print(f"   Model Key: {model_key}")
    print(f"   问题: {question}")
    
    success, response, response_time = call_ai_model(question, model_key, model_name, api_type)
    
    result = {
        'model_name': model_name,
        'model_key': model_key,
        'api_type': api_type,
        'success': success,
        'response': response,
        'response_time': response_time,
        'question': question
    }
    
    if success:
        print(f"   ✅ 成功 ({response_time:.2f}s)")
        print(f"   回答: {response[:100]}{'...' if len(response) > 100 else ''}")
    else:
        print(f"   ❌ 失败 ({response_time:.2f}s)")
        print(f"   错误: {response}")
    
    return result

def test_all_models():
    """测试所有模型"""
    print("🚀 开始测试所有AI模型")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    successful_models = []
    failed_models = []
    
    for model in models:
        try:
            result = test_single_model(
                model['name'], 
                model['model_key'], 
                model['api_type']
            )
            results.append(result)
            
            if result['success']:
                successful_models.append(result)
            else:
                failed_models.append(result)
                
        except Exception as e:
            print(f"❌ 模型 {model['name']} 测试异常: {e}")
            failed_result = {
                'model_name': model['name'],
                'model_key': model['model_key'],
                'api_type': model['api_type'],
                'success': False,
                'error': str(e),
                'response_time': 0
            }
            results.append(failed_result)
            failed_models.append(failed_result)
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"总模型数: {len(results)}")
    print(f"成功: {len(successful_models)}")
    print(f"失败: {len(failed_models)}")
    print(f"成功率: {len(successful_models)/len(results)*100:.1f}%")
    
    if successful_models:
        print("\n✅ 可用模型:")
        for model in successful_models:
            print(f"  - {model['model_name']} ({model['api_type']}) - {model['response_time']:.2f}s")
    
    if failed_models:
        print("\n❌ 不可用模型:")
        for model in failed_models:
            error_msg = model.get('error', model.get('response', '未知错误'))
            print(f"  - {model['model_name']} ({model['api_type']}): {error_msg}")
    
    return results

def test_model_performance():
    """测试模型性能对比"""
    print("\n🏃‍♂️ 开始性能对比测试")
    print("=" * 50)
    
    test_questions = [
        "1+1等于几？",
        "请用一句话介绍人工智能",
        "什么是机器学习？"
    ]
    
    # 只测试前几个模型以节省时间
    test_models = models[:3]
    
    for question in test_questions:
        print(f"\n📝 测试问题: {question}")
        print("-" * 30)
        
        for model in test_models:
            result = test_single_model(
                model['name'], 
                model['model_key'], 
                model['api_type'], 
                question
            )
            if result['success']:
                print(f"  {model['name']}: {result['response'][:50]}...")
            else:
                print(f"  {model['name']}: 测试失败")
        
        time.sleep(2)  # 避免请求过于频繁

if __name__ == "__main__":
    # 测试所有模型
    results = test_all_models()
    
    # 性能对比测试
    test_model_performance()
    
    print("\n✅ 所有测试完成！")