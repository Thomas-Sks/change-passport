// Acceptance tests written by the reviewer (independent from the authoring agent).
using MessagePack.SourceGenerator;
using MessagePack.SourceGenerator.Tests;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Testing;
using Xunit.Abstractions;

public class PassportAcceptanceTests
{
    private readonly ITestOutputHelper output;

    public PassportAcceptanceTests(ITestOutputHelper output) => this.output = output;

    private static async Task<(Compilation Output, ImmutableArray<Diagnostic> Diags)> RunAsync(string source)
    {
        ImmutableArray<MetadataReference> refs = await ReferencesHelper.DefaultTargetFrameworkReferences.ResolveAsync(LanguageNames.CSharp, CancellationToken.None);
        CSharpCompilation compilation = CSharpCompilation.Create(
            "PassportAcceptance",
            [CSharpSyntaxTree.ParseText(source, new CSharpParseOptions(LanguageVersion.Latest))],
            refs.Concat(ReferencesHelper.GetReferences(ReferencesSet.MessagePack)),
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        var driver = CSharpGeneratorDriver.Create(new MessagePackGenerator());
        driver.RunGeneratorsAndUpdateCompilation(compilation, out Compilation outputCompilation, out _);
        return (outputCompilation, outputCompilation.GetDiagnostics());
    }

    // covers: AC-3
    // AC-3 (generated code compiles for all consumers): a user who already marked their own resolver
    // with [ExcludeFromCodeCoverage] must still compile.
    [Fact]
    public async Task UserResolverAlreadyExcluded_StillCompiles()
    {
        const string src = """
            using MessagePack;
            [MessagePackObject] public class MyObject { [Key(0)] public int Value { get; set; } }
            namespace MyNs
            {
                [GeneratedMessagePackResolver]
                [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
                partial class MyResolver { }
            }
            """;
        var (_, diags) = await RunAsync(src);
        var errors = diags.Where(d => d.Severity == DiagnosticSeverity.Error).ToList();
        foreach (var e in errors) this.output.WriteLine(e.ToString());
        Assert.Empty(errors);
    }

    // Refusal R1 evidence: does a user-declared partial resolver (with user-written members)
    // end up excluded from coverage as a whole?
    [Fact]
    public async Task UserResolverMembers_AreExcludedFromCoverage()
    {
        const string src = """
            using MessagePack;
            [MessagePackObject] public class MyObject { [Key(0)] public int Value { get; set; } }
            namespace MyNs
            {
                [GeneratedMessagePackResolver]
                partial class MyResolver
                {
                    public int UserWrittenLogic(int x) => x * 2;
                }
            }
            """;
        var (outputCompilation, _) = await RunAsync(src);
        INamedTypeSymbol? resolver = outputCompilation.GetTypeByMetadataName("MyNs.MyResolver");
        Assert.NotNull(resolver);
        bool excluded = resolver!.GetAttributes().Any(a => a.AttributeClass?.Name == "ExcludeFromCodeCoverageAttribute");
        this.output.WriteLine($"MyResolver excluded from coverage (incl. UserWrittenLogic): {excluded}");
        Assert.False(excluded, "User-written members of a partial resolver are excluded from code coverage.");
    }
}
