use crate::client::GatewayClient;

pub async fn run(client: &GatewayClient) -> anyhow::Result<()> {
    let response = client
        .chat("Show me the collective accomplishments.", "omega")
        .await?;
    println!("{response}");
    Ok(())
}
