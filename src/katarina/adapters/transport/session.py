from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from katarina.adapters.transport.kat1_codec import (
    Kat1Codec,
    Kat1Frame,
    WIRE_MAJOR,
    WIRE_MINOR,
)
from katarina.ports.transport import ReceivedTransportFrame, TransportPeer


HELLO = 1
HELLO_ACK = 2
HEARTBEAT = 3


class SessionState(str, Enum):
    STOPPED = "stopped"
    WAITING_PRESENCE = "waiting_presence"
    HELLO_SENT = "hello_sent"
    RECOVERING = "recovering"
    READY = "ready"
    STALE = "stale"
    FAULTED = "faulted"


@dataclass(frozen=True, slots=True)
class SessionBinding:
    account_id: str
    broker_login: int
    broker_server: str
    stream_id: int
    boot_id: int


@dataclass(frozen=True, slots=True)
class SessionSend:
    frame: bytes
    peer: TransportPeer


class SessionFault(RuntimeError):
    pass


class Kat1SessionSupervisor:
    """Fail-closed Stage-07 KAT1 session/handshake supervisor.

    This class owns communication readiness only. It never grants trading
    readiness. A socket/route, HEARTBEAT, or HELLO_ACK is insufficient by
    itself; the caller must explicitly mark recovery/reconciliation complete.
    """

    def __init__(
        self,
        *,
        codec: Kat1Codec,
        client_instance_id: bytes | str,
        requested_capability_bits: int = 0,
        requested_execution_mode: int = 0,
        last_execution_cursor: int = 0,
        last_snapshot_sequence: int = 0,
        heartbeat_interval_ms: int = 1_000,
        stale_after_ms: int = 5_000,
    ) -> None:
        if isinstance(client_instance_id, str):
            try:
                client_instance_id = bytes.fromhex(client_instance_id)
            except ValueError as exc:
                raise ValueError("client_instance_id must be valid hex") from exc
        if len(client_instance_id) != 16:
            raise ValueError("client_instance_id must be exactly 16 bytes")
        if heartbeat_interval_ms <= 0:
            raise ValueError("heartbeat_interval_ms must be positive")
        if stale_after_ms <= heartbeat_interval_ms:
            raise ValueError(
                "stale_after_ms must be greater than heartbeat_interval_ms"
            )
        if requested_execution_mode != 0:
            raise ValueError(
                "Stage-07 supervisor is communication-only and requires "
                "READ_ONLY execution mode"
            )

        self._codec = codec
        self._client_instance_id = bytes(client_instance_id)
        self._requested_capability_bits = requested_capability_bits
        self._requested_execution_mode = requested_execution_mode
        self._last_execution_cursor = last_execution_cursor
        self._last_snapshot_sequence = last_snapshot_sequence
        self._heartbeat_interval_ns = heartbeat_interval_ms * 1_000_000
        self._stale_after_ns = stale_after_ms * 1_000_000

        self._state = SessionState.STOPPED
        self._binding: SessionBinding | None = None
        self._presence_peer: TransportPeer | None = None
        self._presence_stream_id: int | None = None
        self._presence_boot_id: int | None = None
        self._last_heartbeat_ns: int | None = None
        self._outbound_sequences: dict[int, int] = {}
        self._inbound_sequences: dict[int, int] = {}

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def binding(self) -> SessionBinding | None:
        return self._binding

    @property
    def communication_ready(self) -> bool:
        return self._state is SessionState.READY

    @property
    def live_risk_ready(self) -> bool:
        # Stage 07 does not own or grant live-risk readiness.
        return False

    @property
    def last_heartbeat_ns(self) -> int | None:
        return self._last_heartbeat_ns

    def start(self) -> None:
        if self._state is SessionState.FAULTED:
            raise SessionFault("faulted session supervisor cannot restart")
        self._state = SessionState.WAITING_PRESENCE

    def stop(self) -> None:
        self._state = SessionState.STOPPED
        self._presence_peer = None
        self._presence_stream_id = None
        self._presence_boot_id = None
        self._last_heartbeat_ns = None

    def observe(
        self,
        received: ReceivedTransportFrame,
        *,
        now_ns: int,
    ) -> SessionSend | None:
        if self._state is SessionState.STOPPED:
            raise SessionFault("session supervisor is stopped")
        if self._state is SessionState.FAULTED:
            raise SessionFault("session supervisor is faulted")

        frame = self._codec.decode(received.frame)
        self._validate_transport_metadata(received, frame)
        self._validate_inbound_sequence(frame)

        if frame.header.message_type == HEARTBEAT:
            return self._on_heartbeat(received, frame, now_ns=now_ns)
        if frame.header.message_type == HELLO_ACK:
            self._on_hello_ack(received, frame, now_ns=now_ns)
            return None

        return None

    def reserve_outbound_sequence(
        self,
        *,
        stream_id: int,
        floor: int = 0,
    ) -> int:
        """Reserve the next Python→MT5 KAT1 sequence for any Stage-07 frame.

        All Python producers on one stream must share this lane. Recovery,
        heartbeat and later command orchestration must never maintain separate
        counters.
        """
        if self._state in {SessionState.STOPPED, SessionState.FAULTED}:
            raise SessionFault(
                "cannot reserve outbound sequence while session is stopped/faulted"
            )
        if stream_id <= 0:
            raise ValueError("stream_id must be positive")
        return self._next_outbound_sequence(stream_id, floor=floor)

    def check_stale(self, *, now_ns: int) -> bool:
        if self._last_heartbeat_ns is None:
            return False
        if self._state not in {
            SessionState.HELLO_SENT,
            SessionState.RECOVERING,
            SessionState.READY,
        }:
            return False

        if now_ns - self._last_heartbeat_ns > self._stale_after_ns:
            self._state = SessionState.STALE
            return True
        return False

    def mark_recovered(self, *, now_ns: int) -> None:
        if self._state is not SessionState.RECOVERING:
            raise SessionFault(
                "recovery completion is only valid after HELLO_ACK"
            )
        if self._last_heartbeat_ns is None:
            raise SessionFault("cannot become ready without heartbeat presence")
        if now_ns - self._last_heartbeat_ns > self._stale_after_ns:
            self._state = SessionState.STALE
            raise SessionFault("cannot become ready from a stale heartbeat")
        if self._binding is None:
            self._fault("cannot become ready without a KAT1 binding")
        self._state = SessionState.READY

    def _on_heartbeat(
        self,
        received: ReceivedTransportFrame,
        frame: Kat1Frame,
        *,
        now_ns: int,
    ) -> SessionSend | None:
        self._last_heartbeat_ns = now_ns
        self._presence_peer = received.peer
        self._presence_stream_id = frame.header.stream_id
        self._presence_boot_id = frame.header.boot_id

        if self._state in {
            SessionState.WAITING_PRESENCE,
            SessionState.STALE,
        }:
            hello = self._build_hello(
                peer=received.peer,
                stream_id=frame.header.stream_id,
                boot_id=frame.header.boot_id,
                source_time_ns=now_ns,
                remote_consumed_command_sequence=int(
                    frame.values["latest_consumed_command_sequence"]
                ),
            )
            self._state = SessionState.HELLO_SENT
            return hello

        # Heartbeats refresh freshness but do not imply READY.
        return None

    def _on_hello_ack(
        self,
        received: ReceivedTransportFrame,
        frame: Kat1Frame,
        *,
        now_ns: int,
    ) -> None:
        if self._state is not SessionState.HELLO_SENT:
            self._fault("HELLO_ACK received outside HELLO_SENT state")

        if self._presence_stream_id is None or self._presence_boot_id is None:
            self._fault("HELLO_ACK received before heartbeat presence")

        if frame.header.stream_id != self._presence_stream_id:
            self._fault("HELLO_ACK stream_id differs from presence heartbeat")
        if frame.header.boot_id != self._presence_boot_id:
            self._fault("HELLO_ACK boot_id differs from presence heartbeat")

        ack_stream_id = int(frame.values["stream_id"])
        boot_id_echo = int(frame.values["boot_id_echo"])
        if ack_stream_id != frame.header.stream_id:
            self._fault("HELLO_ACK payload stream_id/header mismatch")
        if boot_id_echo != frame.header.boot_id:
            self._fault("HELLO_ACK boot_id_echo/header mismatch")

        broker_server = frame.values.get("broker_server")
        account_id = frame.values.get("account_id")
        if not isinstance(broker_server, str) or not broker_server:
            self._fault("HELLO_ACK broker_server is empty")
        if not isinstance(account_id, str) or len(account_id) != 32:
            self._fault("HELLO_ACK account_id is invalid")

        candidate = SessionBinding(
            account_id=account_id,
            broker_login=int(frame.values["broker_login"]),
            broker_server=broker_server,
            stream_id=frame.header.stream_id,
            boot_id=frame.header.boot_id,
        )

        if self._binding is not None:
            same_stream = candidate.stream_id == self._binding.stream_id
            if same_stream and (
                candidate.account_id != self._binding.account_id
                or candidate.broker_login != self._binding.broker_login
                or candidate.broker_server != self._binding.broker_server
            ):
                self._fault(
                    "same stream_id rebound to a different account identity"
                )

        self._binding = candidate
        self._last_heartbeat_ns = now_ns
        self._state = SessionState.RECOVERING

    def _build_hello(
        self,
        *,
        peer: TransportPeer,
        stream_id: int,
        boot_id: int,
        source_time_ns: int,
        remote_consumed_command_sequence: int,
    ) -> SessionSend:
        sequence = self._next_outbound_sequence(
            stream_id,
            floor=remote_consumed_command_sequence,
        )
        last_known_stream_id = (
            self._binding.stream_id if self._binding is not None else 0
        )
        frame = self._codec.encode(
            message_type=HELLO,
            schema_version=1,
            sequence=sequence,
            source_time_ns=source_time_ns,
            stream_id=stream_id,
            boot_id=boot_id,
            values={
                "client_instance_id": self._client_instance_id,
                "requested_capability_bits": self._requested_capability_bits,
                "last_known_stream_id": last_known_stream_id,
                "last_execution_cursor": self._last_execution_cursor,
                "requested_execution_mode": self._requested_execution_mode,
                "requested_wire_major": WIRE_MAJOR,
                "requested_wire_minor": WIRE_MINOR,
                "last_snapshot_sequence": self._last_snapshot_sequence,
            },
        )
        return SessionSend(frame=frame, peer=peer)

    def _next_outbound_sequence(self, stream_id: int, *, floor: int = 0) -> int:
        if floor < 0:
            self._fault("remote command sequence floor cannot be negative")
        current = self._outbound_sequences.get(stream_id, 0)
        sequence = max(current, floor) + 1
        self._outbound_sequences[stream_id] = sequence
        return sequence

    def _validate_inbound_sequence(self, frame: Kat1Frame) -> None:
        stream_id = frame.header.stream_id
        sequence = frame.header.sequence
        if sequence <= 0:
            self._fault("KAT1 inbound sequence must be positive")

        previous = self._inbound_sequences.get(stream_id)
        if previous is None:
            self._inbound_sequences[stream_id] = sequence
            return

        if sequence <= previous:
            self._fault("duplicate or decreasing MT5 sequence")
        if sequence != previous + 1:
            self._fault("MT5 sequence gap requires recovery")

        self._inbound_sequences[stream_id] = sequence

    def _validate_transport_metadata(
        self,
        received: ReceivedTransportFrame,
        frame: Kat1Frame,
    ) -> None:
        peer = received.peer
        if (
            peer.stream_id is not None
            and peer.stream_id != frame.header.stream_id
        ):
            self._fault("transport metadata stream_id/KAT1 header mismatch")
        if peer.boot_id is not None and peer.boot_id != frame.header.boot_id:
            self._fault("transport metadata boot_id/KAT1 header mismatch")

    def _fault(self, message: str) -> None:
        self._state = SessionState.FAULTED
        raise SessionFault(message)
