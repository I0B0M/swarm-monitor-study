import { Composition } from "remotion";
import { Explainer } from "./Explainer";
import { TOTAL_FRAMES } from "./timeline";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="Explainer" component={Explainer} durationInFrames={TOTAL_FRAMES} fps={30} width={1920} height={1080} />
    </>
  );
};
