use crate::client::GatewayClient;

pub async fn run(client: &GatewayClient, prompt: Vec<String>) -> anyhow::Result<()> {
    if prompt.is_empty() {
        anyhow::bail!("prompt cannot be empty");
    }
    let text = prompt.join(" ");
    let response = client.chat(&text, "omega").await?;
    println!("{response}");
    Ok(())
}
