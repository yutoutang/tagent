"""
Tests for the pi.agent EventStream class.
"""
import pytest
import asyncio
from pi.agent import EventStream, AssistantMessage, AgentEvent


class TestEventStream:
    """Test EventStream functionality."""

    @pytest.mark.asyncio
    async def test_event_stream_creation(self):
        """Test creating an event stream."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)
        assert stream is not None

    @pytest.mark.asyncio
    async def test_event_stream_push_and_iterate(self):
        """Test pushing events and iterating over them."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Push some events
        stream.push({"type": "event1", "data": "first"})
        stream.push({"type": "event2", "data": "second"})
        stream.push({"type": "done", "result": "finished"})

        # Iterate over events
        events = []
        async for event in stream:
            events.append(event)
            # Stop when we receive done event
            if is_done(event):
                break

        assert len(events) == 3
        assert events[0]["type"] == "event1"
        assert events[1]["type"] == "event2"
        assert events[2]["type"] == "done"

    @pytest.mark.asyncio
    async def test_event_stream_end(self):
        """Test ending a stream with a result."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        stream.end({"type": "done", "result": "final_result"})

        result = await stream.result()
        assert result["result"] == "final_result"

    @pytest.mark.asyncio
    async def test_event_stream_iteration_stops_at_done(self):
        """Test that iteration stops when done event is received."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Push events including done event
        stream.push({"type": "event1"})
        stream.push({"type": "done", "result": "result1"})

        # Push more events after done (should not be received)
        stream.push({"type": "event2"})

        events = []
        async for event in stream:
            events.append(event)
            # Manually break on done
            if is_done(event):
                break

        # Should only receive events up to and including done
        assert len(events) == 2
        assert events[0]["type"] == "event1"
        assert events[1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_event_stream_with_async_producer(self):
        """Test event stream with async event production."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Simulate async event production
        async def produce_events():
            await asyncio.sleep(0.01)
            stream.push({"type": "event1"})

            await asyncio.sleep(0.01)
            stream.push({"type": "event2"})

            await asyncio.sleep(0.01)
            stream.push({"type": "done", "result": "async_result"})

        # Start producer
        task = asyncio.create_task(produce_events())

        # Consume events
        events = []
        async for event in stream:
            events.append(event)
            # Stop on done
            if is_done(event):
                break

        await task

        assert len(events) == 3
        assert events[0]["type"] == "event1"
        assert events[1]["type"] == "event2"
        assert events[2]["type"] == "done"

    @pytest.mark.asyncio
    async def test_event_stream_multiple_consumers(self):
        """Test that multiple consumers can iterate over the same stream."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Push events
        for i in range(5):
            stream.push({"type": f"event{i}", "index": i})
        stream.push({"type": "done", "result": "done"})

        # Create multiple consumers
        async def consumer(name):
            events = []
            async for event in stream:
                events.append(event)
                # Stop on done event
                if event.get("type") == "done":
                    break
            return {name: events}

        # Run consumers concurrently
        results = await asyncio.gather(
            consumer("consumer1"),
            consumer("consumer2"),
        )

        # Both should receive all events
        assert len(results[0]["consumer1"]) == 6
        assert len(results[1]["consumer2"]) == 6

    @pytest.mark.asyncio
    async def test_event_stream_result_before_completion(self):
        """Test getting result before stream is finished."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Don't end the stream yet
        stream.push({"type": "event1"})

        # Try to get result (should wait)
        async def get_result_async():
            return await stream.result()

        task = asyncio.create_task(get_result_async())

        # Wait a bit, should not be done
        await asyncio.sleep(0.05)
        assert not task.done()

        # Now end the stream
        stream.push({"type": "done", "result": "final"})

        # Should complete now
        result = await task
        assert result["result"] == "final"

    @pytest.mark.asyncio
    async def test_event_stream_empty_stream(self):
        """Test iterating over an empty stream."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("result")

        stream = EventStream(is_done, get_result)

        # Immediately end the stream
        stream.end({"type": "done", "result": "empty"})

        # Should be able to iterate (will get done event)
        events = []
        async for event in stream:
            events.append(event)
            # Break on done
            if is_done(event):
                break

        assert len(events) == 1
        assert events[0]["type"] == "done"

    @pytest.mark.asyncio
    async def test_event_stream_complex_events(self):
        """Test stream with complex event structures."""
        def is_done(event):
            return event.get("type") == "agent_end"

        def get_result(event):
            return event.get("messages")

        stream = EventStream(is_done, get_result)

        # Simulate agent lifecycle events
        events_to_push = [
            {"type": "agent_start"},
            {"type": "turn_start"},
            {"type": "message_start", "message": {"role": "user", "content": "Hello"}},
            {"type": "message_end", "message": {"role": "user", "content": "Hello"}},
            {"type": "turn_end", "message": {"role": "assistant", "content": "Hi!"}, "toolResults": []},
            {"type": "agent_end", "messages": [{"role": "user"}, {"role": "assistant"}]},
        ]

        for event in events_to_push:
            stream.push(event)

        # Collect all events
        received = []
        async for event in stream:
            received.append(event)
            # Stop on agent_end
            if event.get("type") == "agent_end":
                break

        assert len(received) == len(events_to_push)
        assert received[0]["type"] == "agent_start"
        assert received[-1]["type"] == "agent_end"

        # Check result
        result = await stream.result()
        assert len(result) == 2
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_event_stream_result_extraction(self):
        """Test extracting result from done event."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            # Extract and transform the result
            return event.get("data", {}).get("value", 0) * 2

        stream = EventStream(is_done, get_result)

        stream.push({"type": "done", "data": {"value": 21}})

        result = await stream.result()
        assert result == 42  # 21 * 2


class TestEventStreamErrorHandling:
    """Test EventStream error handling."""

    @pytest.mark.asyncio
    async def test_stream_with_get_result_error(self):
        """Test stream when get_result raises an error."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            raise ValueError("Cannot extract result")

        stream = EventStream(is_done, get_result)

        stream.push({"type": "done", "result": "test"})

        with pytest.raises(RuntimeError, match="Expected agent_end event"):
            # This will fail because get_result raises
            await stream.result()


class TestEventStreamConcurrency:
    """Test EventStream under concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_push_and_iterate(self):
        """Test pushing events while iterating."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("count", 0)

        stream = EventStream(is_done, get_result)

        received_count = 0

        async def consumer():
            nonlocal received_count
            async for event in stream:
                received_count += 1
                if event.get("type") == "done":
                    break

        async def producer():
            for i in range(10):
                stream.push({"type": "event", "index": i})
                await asyncio.sleep(0.01)
            stream.push({"type": "done", "count": 10})

        # Run consumer and producer concurrently
        await asyncio.gather(
            consumer(),
            producer(),
        )

        assert received_count == 11  # 10 events + 1 done

    @pytest.mark.asyncio
    async def test_rapid_event_production(self):
        """Test stream with rapid event production."""
        def is_done(event):
            return event.get("type") == "done"

        def get_result(event):
            return event.get("count")

        stream = EventStream(is_done, get_result)

        # Push many events rapidly
        for i in range(100):
            stream.push({"type": "event", "index": i})
        stream.push({"type": "done", "count": 100})

        # Consume all events
        count = 0
        async for event in stream:
            count += 1
            # Stop on done event
            if event.get("type") == "done":
                break

        assert count == 101  # 100 events + 1 done
