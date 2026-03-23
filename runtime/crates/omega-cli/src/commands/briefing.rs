use crate::client::GatewayClient;

pub async fn run(client: &GatewayClient) -> anyhow::Result<()> {
    let response = client
        .chat("Give me an activity briefing summary.", "omega")
        .await?;
    println!("{response}");
    Ok(())
}
