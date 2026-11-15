using MessagePack;
namespace Lib;

// Verbatim from issue #2283: a closed generic value type declared in a referenced assembly.
[MessagePackObject]
public partial record struct Item<T>([property: Key(0)] string Key);
