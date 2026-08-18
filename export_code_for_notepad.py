import os

# List of core Python source files in the project
py_files = [
    "app.py",
    "main_agent.py",
    "langgraph_workflow.py",
    "rag_pipeline.py",
    "mock_mcp_servers.py"
]

output_filename = "ALL_SOURCE_CODE.txt"

with open(output_filename, "w", encoding="utf-8") as outfile:
    outfile.write("========================================================================\n")
    outfile.write("    ABC TECHNOLOGIES - ENTERPRISE AI SUPPORT ASSISTANT SOURCE CODE      \n")
    outfile.write("========================================================================\n\n")

    for filename in py_files:
        if os.path.exists(filename):
            outfile.write(f"########################################################################\n")
            outfile.write(f"# FILE: {filename}\n")
            outfile.write(f"########################################################################\n\n")
            with open(filename, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
            outfile.write("\n\n" + "="*72 + "\n\n")

print(f"Successfully generated {output_filename} containing all Python source code for Notepad & Email!")
