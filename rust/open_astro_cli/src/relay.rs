use tokio::net::{TcpListener, TcpStream};
use tokio::io;
use anyhow::{Result, Context};

pub async fn bind_relay(listen_addr: &str) -> Result<TcpListener> {
    TcpListener::bind(listen_addr)
        .await
        .context("Failed to bind TCP listener")
}

pub async fn proxy_stream(mut client: TcpStream, target_addr: &str) -> Result<()> {
    let mut upstream = TcpStream::connect(target_addr)
        .await
        .context("Failed to connect to target address")?;

    io::copy_bidirectional(&mut client, &mut upstream)
        .await
        .context("Failed to copy data between streams")?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::TcpStream;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    #[tokio::test]
    async fn test_relay() -> Result<()> {
        // Start an echo server on a random port
        let echo_server = TcpListener::bind("127.0.0.1:0")
            .await
            .context("Failed to bind echo server")?;
        let echo_server_addr = echo_server.local_addr().context("Failed to get echo server address")?;

        tokio::spawn(async move {
            let (mut client, _) = echo_server.accept().await.unwrap();
            let mut buf = [0; 1024];
            let n = client.read(&mut buf).await.unwrap();
            client.write_all(&buf[..n]).await.unwrap();
        });

        // Bind the relay on a random port
        let relay = bind_relay("127.0.0.1:0").await?;
        let relay_addr = relay.local_addr().context("Failed to get relay address")?;

        tokio::spawn(async move {
            let (client, _) = relay.accept().await.unwrap();
            proxy_stream(client, &echo_server_addr.to_string()).await.unwrap();
        });

        // Connect to the relay and send a message
        let mut client = TcpStream::connect(relay_addr).await?;
        client.write_all(b"RCMP_PING").await?;

        // Read the echoed response
        let mut buf = [0; 1024];
        let n = client.read(&mut buf).await?;
        assert_eq!(&buf[..n], b"RCMP_PING");

        Ok(())
    }
}
