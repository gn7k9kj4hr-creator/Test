from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import os
from dotenv import load_dotenv

load_dotenv()

class StrategyGenerator:
    def __init__(self):
        self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), model_name="gpt-3.5-turbo", temperature=0.7)

    def generate_strategy(self, iteration=1, previous_results="None"):
        prompt = PromptTemplate(
            input_variables=["iteration", "previous_results"],
            template="""Generate a NEW paper-trading strategy for penny stocks with:
1. Entry condition (technical indicators)
2. Exit condition (profit target or stop loss)
3. Risk/reward ratio
4. Position sizing
5. Market conditions
6. Indicator list

Format as JSON only: {name, entry_condition, exit_condition, risk_reward, position_size, market_conditions, indicator_list}
Iteration: {iteration}
Previous Results: {previous_results}"""
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(iteration=iteration, previous_results=previous_results)
        try:
            return json.loads(response)
        except (TypeError, json.JSONDecodeError):
            return None
