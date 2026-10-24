/**
 * ZK_STUB: sha256-based mock of Poseidon(Poseidon(raw_id, user_salt), PROTOCOL_SALT)
 * (zk-identity-stub skill). NOT a real zero-knowledge proof; UI copy must say
 * "simulated identity anchor".
 */
async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
}

/** ZK_STUB: deterministic, so re-registering the same demo ID resolves to the same record. */
export async function nullifierStub(
  rawId: string,
  userSalt: string,
  protocolSalt: string,
): Promise<string> {
  const sk = await sha256Hex(`${rawId}:${userSalt}`);
  return `0x${await sha256Hex(`${sk}:${protocolSalt}`)}`;
}
