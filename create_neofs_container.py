import os
import sys
from dotenv import load_dotenv

# Add spoon-core to path
sys.path.append(os.path.join(os.getcwd(), "spoon-core"))

from spoon_ai.neofs import NeoFSClient
from spoon_ai.neofs.models import Bearer, Rule, ContainerPostInfo

# Load env vars
load_dotenv()

def main():
    print("Initializing NeoFS Client...")
    try:
        client = NeoFSClient()
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"Owner Address: {client.owner_address}")
    
    # 1. Create Bearer Token for Container Creation
    print("Creating Bearer Token...")
    
    # Rule for creating a container (PUT verb, empty containerId)
    rule = Rule(verb="PUT", containerId="")
    bearer_token_request = Bearer(
        name="container-creation-token",
        container=rule
    )
    
    try:
        tokens = client.create_bearer_tokens([bearer_token_request], lifetime=300) # 5 minutes
        bearer_token = tokens[0].token
        print(f"Bearer Token created: {bearer_token[:10]}...")
    except Exception as e:
        print(f"Failed to create bearer token: {e}")
        return

    # 2. Create Container
    container_name = "mindtrace-data"
    print(f"Creating Container '{container_name}'...")
    
    container_info = ContainerPostInfo(
        containerName=container_name,
        basicAcl="public-read-write", 
        placementPolicy="REP 1" 
    )
    
    try:
        container = client.create_container(
            container_info, 
            bearer_token, 
            name_scope_global=True
        )
        print(f"✅ Container Created Successfully!")
        print(f"Container ID: {container.container_id}")
        print(f"Container Name: {container.container_name}")
        
        # Update .env file
        update_env_file(container.container_id)
        
    except Exception as e:
        print(f"❌ Failed to create container: {e}")
        if "402" in str(e) or "payment" in str(e).lower() or "balance" in str(e).lower():
            print("\n⚠️  Insufficient GAS. You need GAS in your Neo N3 wallet to create a container.")
            print(f"Wallet Address: {client.owner_address}")
            print("You can get free Testnet GAS from a faucet: https://neowish.ngd.network/")

def update_env_file(container_id):
    env_path = ".env"
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("NEOFS_CONTAINER_ID="):
                new_lines.append(f"NEOFS_CONTAINER_ID={container_id}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"NEOFS_CONTAINER_ID={container_id}\n")
                
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        print(f"Updated .env with Container ID.")
    except Exception as e:
        print(f"Failed to update .env: {e}")

if __name__ == "__main__":
    main()
