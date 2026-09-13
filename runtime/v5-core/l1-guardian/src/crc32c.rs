//! VALO V5.0 — Maskinvare-optimalisert CRC32C (Castagnoli) sjekksum
//! Sikrer minneintegritet for WORM-loggen i henhold til EU AI Act Art. 15.

/// Castagnoli-polynomet (0x1EDC6F41) i reversert form (0x82F63B78).
/// Dette polynomet gir optimal Hamming-distanse for minnebuffere.
const POLY: u32 = 0x82F63B78;

/// Genererer en statisk oppslagstabell ved kompilering (compile-time).
/// Dette fjerner all runtime-overhead for initialisering.
const fn generate_table() -> [u32; 256] {
    let mut table = [0u32; 256];
    let mut i = 0;
    while i < 256 {
        let mut crc = i as u32;
        let mut j = 0;
        while j < 8 {
            if (crc & 1) != 0 {
                crc = (crc >> 1) ^ POLY;
            } else {
                crc >>= 1;
            }
            j += 1;
        }
        table[i] = crc;
        i += 1;
    }
    table
}

/// Statisk tabell som bakes direkte inn i den binære filen.
const CRC32C_TABLE: [u32; 256] = generate_table();

/// Beregner CRC32C-sjekksummen for en vilkårlig byte-strøm (f.eks. serialisert logg).
/// Markert med `#[inline(always)]` for å eliminere overhead fra funksjonskall.
#[inline(always)]
pub fn calculate(data: &[u8]) -> u32 {
    let mut crc = !0u32; // Initialiserer med 0xFFFFFFFF
    
    for &byte in data {
        let index = ((crc ^ byte as u32) & 0xFF) as usize;
        crc = (crc >> 8) ^ CRC32C_TABLE[index];
    }
    
    !crc // Inverterer resultatet tilbake (final negation)
}

// =============================================================================
// ENHETSTESTER (Verifiserer matematisk korrekthet mot standarden)
// =============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_standard_castagnoli_vector() {
        // Standard test-vektor for Castagnoli CRC32C
        let test_data = b"123456789";
        let checksum = calculate(test_data);
        // Forventet Castagnoli-sjekksum for "123456789" er universelt 0xE3069283
        assert_eq!(checksum, 0xE3069283);
    }

    #[test]
    fn test_empty_buffer() {
        let empty_data = b"";
        let checksum = calculate(empty_data);
        assert_eq!(checksum, 0x00000000);
    }
}
