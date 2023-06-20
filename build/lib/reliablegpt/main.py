import openai
from termcolor import colored
import time
import functools
import copy

CHAT_MODELS = [
    'gpt-4',
    'gpt-4-0613',
    'gpt-4-32k',
    'gpt-4-32k-0613'
    'gpt-3.5-turbo'
    'gpt-3.5-turbo-16k',
    'gpt-3.5-turbo-0613'
]

TEXT_MODELS = [
    'text-davinci-003',
    'text-davinci-002',
    'text-curie-001',
    'ada',
    'babbage'
]

def make_LLM_request(new_kwargs):
    try:
        model = new_kwargs['model']
        #print(kwargs)
        # print(model)
        if "3.5" or "4" in model:
            print(colored(f"ReliableGPT: Retrying request with model CHAT {model}", "blue"))
            return openai.ChatCompletion.create(**new_kwargs)
        else:
            print(colored(f"ReliableGPT: Retrying request with model TEXT {model}", "blue"))
            new_kwargs['prompt'] = " ".join([message["content"] for message in new_kwargs['messages']])
            new_kwargs.pop('messages', None) # remove messages for completion models 
            return openai.Completion.create(**new_kwargs)
    except Exception as e:
        print(colored(f"ReliableGPT: Got 2nd Error {e}", "red"))
        return None
    return None

def fallback_request(fallback_strategy, kwargs):
    result = None
    start_time = time.time()
    # print(fallback_strategy)
    for model in fallback_strategy:
        new_kwargs = copy.deepcopy(kwargs)  # Create a deep copy of kwargs
        new_kwargs['model'] = model  # Update the model
        result = make_LLM_request(new_kwargs)
        if result != None:
            return result
    return None

def handle_openAI_error(openAI_error, kwargs, fallback_strategy=[], graceful_string="Sorry, the OpenAI (GPT) failed"):
    # Error Types from https://platform.openai.com/docs/guides/error-codes/python-library-error-types
    # 1. APIError - retry, retry with fallback
    # 2. Timeout - retry, retry with fallback
    # 3. RateLimitError - retry, retry with fallback
    # 4. APIConnectionError - Check your network settings, proxy configuration, SSL certificates, or firewall rules.
    # 5. InvalidRequestError - User input was bad: context_length_exceeded, 
    # 6. AuthenticationError - API key not working, return default hardcoded message
    # 7. ServiceUnavailableError - retry, retry with fallback
    if fallback_strategy == []:
        fallback_strategy = ['gpt-3.5-turbo', 'text-davinci-003', 'gpt-4', 'text-davinci-002']
    error_type = openAI_error['type']
    if error_type == 'invalid_request_error' or error_type == 'InvalidRequestError':
        print(colored("ReliableGPT: invalid request error", "red"))
        # check if this is context window related, try with a 16k model
        if openAI_error.code == 'context_length_exceeded':
            fallback_strategy = ['gpt-3.5-turbo-16k'] + fallback_strategy
            result = fallback_request(fallback_strategy, kwargs)
            if result == None:
                return graceful_string
            else:
                return result

    elif error_type == 'authentication_error' or error_type == 'AuthenticationError':
        print(colored("ReliableGPT: Auth error", "red"))
        return graceful_string

    # catch all 
    result = fallback_request(fallback_strategy, kwargs)
    if result == None:
        return graceful_string
    else:
        return result
    return graceful_string


def reliable_create(func):
    @functools.wraps(func)
    def decorator_wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            return response
        except Exception as e:
            print(colored(f"ReliableGPT: Error Response from openai.ChatCompletion.create()", 'red'))
            print(colored(f"ReliableGPT: Got Exception {e}", 'red'))
            # print({e.code})
            # print(e.error)
            result = handle_openAI_error(e.error, kwargs)
            print(colored(f"ReliableGPT: Recoverd got a successfull response {result}", "green"))
            return handle_openAI_error(e.error, kwargs)

    return decorator_wrapper


