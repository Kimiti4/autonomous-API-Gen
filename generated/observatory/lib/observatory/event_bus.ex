defmodule Tiannara.Observatory.EventBus do
  @moduledoc """
  Observatory event bus.

  Persists events to the Store and broadcasts them to subscribers.

  Topics:
  - observatory:events:<subject_id>
  - observatory:events:category:<category>
  - observatory:events:*
  """

  require Logger

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Store

  @topic_prefix "observatory:events:"

  @spec publish(Event.t()) :: :ok
  def publish(%Event{} = event) do
    :ok = Store.write(event)
    broadcast(event)
    :ok
  end

  @spec subscribe_subject(String.t()) :: :ok | {:error, term()}
  def subscribe_subject(subject_id) when is_binary(subject_id) do
    Phoenix.PubSub.subscribe(pubsub(), subject_topic(subject_id))
  end

  @spec unsubscribe_subject(String.t()) :: :ok | {:error, term()}
  def unsubscribe_subject(subject_id) when is_binary(subject_id) do
    Phoenix.PubSub.unsubscribe(pubsub(), subject_topic(subject_id))
  end

  @spec subscribe_category(atom()) :: :ok | {:error, term()}
  def subscribe_category(category) when is_atom(category) do
    Phoenix.PubSub.subscribe(pubsub(), category_topic(category))
  end

  @spec unsubscribe_category(atom()) :: :ok | {:error, term()}
  def unsubscribe_category(category) when is_atom(category) do
    Phoenix.PubSub.unsubscribe(pubsub(), category_topic(category))
  end

  @spec subscribe_all() :: :ok | {:error, term()}
  def subscribe_all do
    Phoenix.PubSub.subscribe(pubsub(), all_topic())
  end

  @spec unsubscribe_all() :: :ok | {:error, term()}
  def unsubscribe_all do
    Phoenix.PubSub.unsubscribe(pubsub(), all_topic())
  end

  defp broadcast(event) do
    try do
      Phoenix.PubSub.broadcast(
        pubsub(),
        subject_topic(event.subject_id),
        {:observatory_event, event}
      )

      Phoenix.PubSub.broadcast(
        pubsub(),
        category_topic(event.category),
        {:observatory_event, event}
      )

      Phoenix.PubSub.broadcast(
        pubsub(),
        all_topic(),
        {:observatory_event, event}
      )
    rescue
      error ->
        Logger.warning(
          "Observatory event broadcast failed: #{inspect(error)}"
        )
    end
  end

  defp pubsub do
    Application.get_env(:tiannara_observatory, :pubsub, Tiannara.PubSub)
  end

  defp subject_topic(subject_id) do
    @topic_prefix <> subject_id
  end

  defp category_topic(category) do
    @topic_prefix <> "category:" <> Atom.to_string(category)
  end

  defp all_topic do
    @topic_prefix <> "*"
  end
end
