#[derive(Debug, PartialEq, Clone, Copy)]
pub enum DistrustLevel {
    L0Trusted,
    L1Monitor,
    L2Caution,
    L3Suspicious,
    L4Untrusted,
}

#[derive(Debug, Clone, Copy)]
pub struct WeatherData {
    pub temperature: f32,
    pub humidity: f32,
}

#[derive(Debug, Clone, Copy)]
pub struct MarketData {
    pub volatility: f32,
    pub volume: u64,
}

pub struct ContextConfig {
    pub update_interval_ms: u32,
}

pub struct ContextPacket {
    pub level: DistrustLevel,
    pub timestamp: u64,
}

pub struct ContextEngine {
    pub current_level: DistrustLevel,
}
