import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("React error boundary caught:", error, info);
  }

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            padding: 32,
            maxWidth: 720,
            margin: "40px auto",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            color: "var(--text-primary)",
            fontFamily: "inherit",
          }}
        >
          <h2 style={{ marginBottom: 12, color: "var(--danger)" }}>
            Something went wrong
          </h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: 16 }}>
            The UI hit an unexpected error and stopped rendering. The page won't
            go blank — you can recover here. Details below:
          </p>
          <pre
            style={{
              background: "var(--bg-secondary)",
              padding: 12,
              borderRadius: "var(--radius)",
              overflowX: "auto",
              fontSize: "0.8rem",
              color: "var(--danger)",
              marginBottom: 16,
              whiteSpace: "pre-wrap",
            }}
          >
            {this.state.error.message}
            {"\n\n"}
            {this.state.error.stack}
          </pre>
          <button className="primary" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
